import test from "node:test";
import assert from "node:assert/strict";
import { createCsrfTransport, csrfFailureKind } from "./csrfTransport.mjs";

const origin = "https://rcon3.example.test";
const json = (status = 200, headers = {}, body = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
const rejection = () =>
  json(403, {
    "X-CRCON-CSRF-Recovery": "1",
    "X-CRCON-CSRF-Error": "token",
    "X-CRCON-CSRF-Token": "do-not-cache-a-late-rejection",
  });
const deferred = () => {
  let resolve;
  const promise = new Promise((done) => {
    resolve = done;
  });
  return { promise, resolve };
};

function harness({ override, visibleCookie } = {}) {
  const state = { cookie: "", secret: "initial", calls: [], executed: [] };
  const transport = createCsrfTransport({
    apiBase: "/api/",
    pageOrigin: origin,
    readCookie: () => (visibleCookie ? visibleCookie(state) : state.cookie),
    fetcher: async (input, options = {}) => {
      const url = new URL(input, origin);
      const command = url.pathname.split("/").at(-1);
      const sentToken = new Headers(options.headers).get("X-CSRFToken");
      state.calls.push({ command, sentToken, ...options });
      if (override) {
        const response = await override({ command, options, state, sentToken });
        if (response) return response;
      }
      if (command === "is_logged_in") {
        state.cookie = `csrftoken=${state.secret}`;
        return json(
          200,
          { "X-CRCON-CSRF-Token": state.secret },
          {
            result: { authenticated: true },
          }
        );
      }
      if (command === "logout") return json();
      if (options.method && options.method !== "GET") {
        if (sentToken !== state.secret) return rejection();
        state.executed.push(command);
      }
      if (command === "login") {
        state.secret = "rotated-by-login";
        state.cookie = `csrftoken=${state.secret}`;
        return json(200, { "X-CRCON-CSRF-Token": state.secret });
      }
      return json();
    },
  });
  const write = (name = "kick", options = {}) =>
    transport.fetchWithCsrf(`${origin}/api/${name}`, {
      method: "POST",
      body: '{"player_id":"test"}',
      ...options,
    });
  const check = () => transport.fetchWithCsrf(`${origin}/api/is_logged_in`);
  const checks = () =>
    state.calls.filter((call) => call.command === "is_logged_in");
  return { state, transport, write, check, checks };
}

test("missing-cookie bootstrap is shared by startup and concurrent writes", async () => {
  const h = harness();
  const results = await Promise.all([
    h.check(),
    h.write("kick"),
    h.write("save"),
  ]);
  assert.deepEqual(
    results.map((response) => response.status),
    [200, 200, 200]
  );
  assert.equal(h.checks().length, 1);
  assert.deepEqual(h.state.executed, ["kick", "save"]);
  assert.equal(h.checks()[0].cache, "no-store");
  assert.equal(h.checks()[0].credentials, "include");
  assert.deepEqual(await results[0].json(), {
    result: { authenticated: true },
  });
});

test("server token wins over duplicate/stale document cookies", async () => {
  const h = harness({
    visibleCookie: (s) => `csrftoken=wrong-path; ${s.cookie}`,
  });
  assert.equal((await h.write()).status, 200);
  assert.equal(h.state.calls.at(-1).sentToken, "initial");
  assert.equal(h.state.calls.length, 2);
});

test("login immediately replaces the old token without a rejected follow-up write", async () => {
  const h = harness();
  await h.write("save");
  await h.write("login");
  const before = h.state.calls.length;
  await h.write("kick");
  assert.equal(h.state.calls.length - before, 1);
  assert.equal(h.state.calls.at(-1).sentToken, "rotated-by-login");
  assert.deepEqual(h.state.executed, ["save", "login", "kick"]);
});

test("logout and explicit expiry reset cached tokens", async () => {
  const h = harness();
  await h.check();
  await h.transport.fetchWithCsrf(`${origin}/api/logout`);
  await h.write();
  h.transport.reset();
  await h.write("save");
  assert.equal(h.checks().length, 3);
});

test("cookie rotation in another tab is noticed before the next write", async () => {
  const h = harness();
  await h.check();
  h.state.secret = "another-tab";
  h.state.cookie = "csrftoken=another-tab";
  await h.write();
  assert.equal(h.checks().length, 2);
  assert.equal(h.state.calls.at(-1).sentToken, "another-tab");
  assert.equal(h.state.calls.filter((c) => c.command === "kick").length, 1);
});

test("simultaneous token rejections share refresh and execute each action once", async () => {
  // Cookie is not readable in a cross-origin API setup; simulate server rotation.
  const h = harness({ visibleCookie: () => "" });
  await h.check();
  h.state.secret = "new-token";
  const results = await Promise.all([h.write("kick"), h.write("save")]);
  assert.deepEqual(
    results.map((r) => r.status),
    [200, 200]
  );
  assert.equal(h.checks().length, 2);
  assert.deepEqual(h.state.executed, ["kick", "save"]);
  for (const name of ["kick", "save"]) {
    const attempts = h.state.calls.filter((c) => c.command === name);
    assert.equal(attempts.length, 2);
    assert.equal(attempts[0].body, attempts[1].body);
    assert.equal(attempts[1].sentToken, "new-token");
  }
});

test("a delayed rejection uses the already refreshed token, not its stale header", async () => {
  const late = deferred();
  const started = deferred();
  let rejectLate = true;
  const h = harness({
    visibleCookie: () => "",
    override: async ({ command }) => {
      if (command === "late" && rejectLate) {
        rejectLate = false;
        started.resolve();
        await late.promise;
        return rejection();
      }
    },
  });
  await h.check();
  h.state.secret = "new-token";
  const waiting = h.write("late");
  await started.promise;
  await h.write("kick");
  late.resolve();
  assert.equal((await waiting).status, 200);
  assert.equal(h.checks().length, 2);
  assert.deepEqual(h.state.executed, ["kick", "late"]);
});

test("a persistent token rejection has exactly one retry", async () => {
  const h = harness({
    override: ({ command }) => command === "kick" && rejection(),
  });
  assert.equal((await h.write()).status, 403);
  assert.equal(h.state.calls.filter((c) => c.command === "kick").length, 2);
  assert.equal(h.state.executed.length, 0);
});

for (const [label, status, headers] of [
  ["permission", 403, {}],
  ["origin", 403, { "X-CRCON-CSRF-Error": "request" }],
  [
    "origin even with inconsistent recovery marker",
    403,
    {
      "X-CRCON-CSRF-Error": "request",
      "X-CRCON-CSRF-Recovery": "1",
    },
  ],
  ["expired authentication", 401, {}],
  ["server error", 500, {}],
  ["timeout", 504, {}],
]) {
  test(`${label} failures never replay the action`, async () => {
    const h = harness({
      override: ({ command }) => command === "kick" && json(status, headers),
    });
    assert.equal((await h.write()).status, status);
    assert.equal(h.state.calls.filter((c) => c.command === "kick").length, 1);
    assert.equal(h.checks().length, 1);
  });
}

test("a lost response after executing an action never causes a retry", async () => {
  let executions = 0;
  const h = harness({
    override: ({ command }) => {
      if (command === "kick") {
        executions++;
        throw new TypeError("network lost");
      }
    },
  });
  await assert.rejects(h.write(), /network lost/);
  assert.equal(executions, 1);
});

test("failed bootstrap prevents the original action", async () => {
  const h = harness({
    override: ({ command }) => command === "is_logged_in" && json(503),
  });
  await assert.rejects(h.write(), { code: "refresh_failed" });
  assert.equal(h.state.calls.length, 1);
});

test("failed recovery leaves the rejection and does not retry an action", async () => {
  const h = harness({
    override: ({ command, state }) => {
      if (command === "kick") return rejection();
      if (command === "is_logged_in" && state.calls.length > 1)
        throw new Error("offline");
    },
  });
  assert.equal((await h.write()).status, 403);
  assert.equal(h.state.calls.filter((c) => c.command === "kick").length, 1);
});

test("logout during bootstrap cancels a pending write", async () => {
  const gate = deferred();
  const started = deferred();
  let first = true;
  const h = harness({
    override: async ({ command }) => {
      if (command === "is_logged_in" && first) {
        first = false;
        started.resolve();
        await gate.promise;
      }
    },
  });
  const waiting = h.write();
  const rejected = assert.rejects(waiting, { code: "session_changed" });
  await started.promise;
  await h.transport.fetchWithCsrf(`${origin}/api/logout`);
  gate.resolve();
  await rejected;
  assert.equal(h.state.executed.length, 0);
});

test("logout while a rejection is in flight prevents automatic replay", async () => {
  const gate = deferred();
  const started = deferred();
  const h = harness({
    override: async ({ command }) => {
      if (command === "kick") {
        started.resolve();
        await gate.promise;
        return rejection();
      }
    },
  });
  await h.check();
  const waiting = h.write();
  await started.promise;
  await h.transport.fetchWithCsrf(`${origin}/api/logout`);
  gate.resolve();
  assert.equal((await waiting).status, 403);
  assert.equal(h.state.calls.filter((c) => c.command === "kick").length, 1);
});

test("aborting one waiter does not cancel the shared token refresh for others", async () => {
  const h = harness();
  const controller = new AbortController();
  const first = h.write("aborted", { signal: controller.signal });
  const second = h.write("save");
  controller.abort();
  await assert.rejects(first, { name: "AbortError" });
  assert.equal((await second).status, 200);
  assert.equal(h.checks().length, 1);
  assert.deepEqual(h.state.executed, ["save"]);
});

test("tokens and bootstrap are restricted to the configured session API", async () => {
  const h = harness();
  await h.check();
  for (const url of [
    "https://other.example/api/save",
    `${origin}/accounts/password_change/`,
    `${origin}/api-other/save`,
  ]) {
    await h.transport.fetchWithCsrf(url, { method: "POST" });
    assert.equal(h.state.calls.at(-1).sentToken, null);
  }
  await h.write("service", { headers: { Authorization: "Bearer test" } });
  // Authorization does not imply the absence of a browser session cookie.
  assert.equal(h.state.calls.at(-1).sentToken, "initial");
  assert.equal(new Headers(h.state.calls.at(-1).headers).get("Authorization"), "Bearer test");
  await h.write("anonymous", { credentials: "omit" });
  assert.equal(h.state.calls.at(-1).sentToken, null);
  assert.equal(h.checks().length, 1);
});

test("legacy HTML CSRF failures stay distinguishable from permission errors", () => {
  assert.equal(
    csrfFailureKind(
      new Response("<html>Forbidden</html>", {
        status: 403,
        headers: { "X-CRCON-CSRF-Recovery": "1" },
      })
    ),
    "token"
  );
  assert.equal(csrfFailureKind(json(403)), null);
  assert.equal(
    csrfFailureKind(json(200, { "X-CRCON-CSRF-Error": "token" })),
    null
  );
});

test("older APIs still work with a single valid cookie during rolling updates", async () => {
  const h = harness({
    override: ({ command, state }) => {
      if (command === "is_logged_in") {
        state.secret = "a".repeat(32);
        state.cookie = `csrftoken=${state.secret}`;
        return json(); // Previous API has no authoritative auth-response header.
      }
    },
  });
  assert.equal((await h.write()).status, 200);
  assert.equal(h.state.calls.filter((c) => c.command === "kick").length, 1);
});

test("a cross-origin API uses its own authoritative token, never the UI cookie", async () => {
  const seen = [];
  const transport = createCsrfTransport({
    apiBase: "https://api.example.test/api/",
    pageOrigin: origin,
    readCookie: () => "csrftoken=wrong-ui-cookie",
    fetcher: async (url, options) => {
      seen.push(options);
      return json(200, { "X-CRCON-CSRF-Token": "api-token" });
    },
  });
  await transport.fetchWithCsrf("https://api.example.test/api/save", {
    method: "POST",
  });
  assert.equal(
    new Headers(seen.at(-1).headers).get("X-CSRFToken"),
    "api-token"
  );
  const before = seen.length;
  await transport.fetchWithCsrf("https://api.example.test/api/save", {
    method: "POST",
    credentials: "same-origin",
  });
  assert.equal(seen.length - before, 1);
  assert.equal(new Headers(seen.at(-1).headers).get("X-CSRFToken"), null);
});
