import { test, expect } from "@playwright/test";

// Real browser cookies + the production CSRF transport + real Django auth/views.
// Only the opt-in isolated smoke server is used; no game commands exist there.
async function start(page, context) {
  if (process.env.RELEASE_SMOKE_BACKEND_URL) {
    // nginx deliberately proxies only /api/. Forward ONLY the two opt-in
    // fixture resources to the isolated backend, leaving every real auth/API
    // request, cookie and Origin check on the production frontend proxy.
    for (const path of ["/__test__/blank", "/__test__/csrf-transport.mjs"]) {
      await page.route((url) => url.pathname === path, async (route) => {
        const response = await context.request.get(
          new URL(path, process.env.RELEASE_SMOKE_BACKEND_URL).href
        );
        expect(response.ok()).toBe(true);
        await route.fulfill({ response });
      });
    }
  }
  const login = await context.request.post("/api/login", {
    data: { username: "csrf", password: "isolated-test-only" },
  });
  expect(login.status()).toBe(200);
  await page.goto("/__test__/blank");
  await page.evaluate(async () => {
    const { createCsrfTransport } = await import(
      "/__test__/csrf-transport.mjs"
    );
    window.attempts = [];
    window.transport = createCsrfTransport({
      apiBase: "/api/",
      pageOrigin: location.origin,
      readCookie: () => document.cookie,
      fetcher: async (...args) => {
        window.beforeRequest?.(...args);
        const response = await fetch(...args);
        window.attempts.push({
          path: new URL(args[0], location.origin).pathname,
          status: response.status,
        });
        return response;
      },
    });
    window.save = () =>
      window.transport.fetchWithCsrf("/api/set_own_user_appearance", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset: "wardogs", mode: "dark" }),
      });
  });
}

test("missing cookie: parallel browser writes bootstrap once and all succeed", async ({
  page,
  context,
}) => {
  await start(page, context);
  await context.clearCookies({ name: "csrftoken" });
  const result = await page.evaluate(async () => ({
    statuses: await Promise.all([
      window.save(),
      window.save(),
      window.save(),
    ]).then((responses) => responses.map((r) => r.status)),
    attempts: window.attempts,
  }));
  expect(result.statuses).toEqual([200, 200, 200]);
  expect(
    result.attempts.filter((r) => r.path === "/api/is_logged_in")
  ).toHaveLength(1);
  expect(result.attempts.filter((r) => r.status === 403)).toHaveLength(0);
});

test("duplicate path cookies: use the server-derived token on the first write", async ({
  page,
  context,
}) => {
  await start(page, context);
  await page.evaluate(() => {
    document.cookie = `csrftoken=${"z".repeat(32)}; Path=/__test__/`;
  });
  expect(
    await page.evaluate(() => document.cookie.split("csrftoken=").length - 1)
  ).toBe(2);
  expect(await page.evaluate(async () => (await window.save()).status)).toBe(
    200
  );
  expect(
    await page.evaluate(() => window.attempts.filter((r) => r.status === 403))
  ).toHaveLength(0);
});

test("a real Django token rejection refreshes once and only the retry saves", async ({
  page,
  context,
}) => {
  await start(page, context);
  const result = await page.evaluate(async () => {
    await window.transport.fetchWithCsrf("/api/is_logged_in");
    window.beforeRequest = (_input, options) => {
      if (options.method === "PUT") {
        // Rotate between header construction and browser cookie attachment,
        // reproducing a concurrent login/cookie change during a write.
        document.cookie = `csrftoken=${"b".repeat(32)}; Path=/`;
        window.beforeRequest = null;
      }
    };
    const response = await window.save();
    return { status: response.status, attempts: window.attempts };
  });
  expect(result.status).toBe(200);
  expect(
    result.attempts
      .filter((r) => r.path === "/api/set_own_user_appearance")
      .map((r) => r.status)
  ).toEqual([403, 200]);
  expect(
    result.attempts.filter((r) => r.path === "/api/is_logged_in")
  ).toHaveLength(2);
});

test("login rotates the token; the next browser write succeeds without recovery", async ({
  page,
  context,
}) => {
  await start(page, context);
  const result = await page.evaluate(async () => {
    await window.save();
    const before = document.cookie;
    const login = await window.transport.fetchWithCsrf("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: "csrf",
        password: "isolated-test-only",
      }),
    });
    const callsAfterLogin = window.attempts.length;
    const saved = await window.save();
    return {
      login: login.status,
      saved: saved.status,
      rotated: before !== document.cookie,
      afterLogin: window.attempts.slice(callsAfterLogin),
    };
  });
  expect(result).toEqual({
    login: 200,
    saved: 200,
    rotated: true,
    afterLogin: [{ path: "/api/set_own_user_appearance", status: 200 }],
  });
});

test("another tab rotates the cookie; an existing tab refreshes before writing", async ({
  page,
  context,
}) => {
  await start(page, context);
  await page.evaluate(() => window.save());
  const csrfCookie = (await context.cookies()).find(
    (cookie) => cookie.name === "csrftoken"
  ).value;
  const login = await context.request.post("/api/login", {
    headers: { "X-CSRFToken": csrfCookie },
    data: { username: "csrf", password: "isolated-test-only" },
  });
  expect(login.status()).toBe(200);
  expect(await page.evaluate(async () => (await window.save()).status)).toBe(
    200
  );
  expect(
    await page.evaluate(() => window.attempts.filter((r) => r.status === 403))
  ).toHaveLength(0);
});

test("bad origin is rejected without recovery, while a missing token has a JSON contract", async ({
  context,
}) => {
  await context.request.post("/api/login", {
    data: { username: "csrf", password: "isolated-test-only" },
  });
  const denied = await context.request.put("/api/set_own_user_appearance", {
    headers: { Origin: "https://attacker.invalid" },
    data: { mode: "light" },
  });
  expect(denied.status()).toBe(403);
  expect(denied.headers()["x-crcon-csrf-error"]).toBe("request");
  expect(denied.headers()["x-crcon-csrf-recovery"]).toBeUndefined();
  const missing = await context.request.put("/api/set_own_user_appearance", {
    data: { mode: "light" },
  });
  expect(missing.status()).toBe(403);
  expect((await missing.json()).error_code).toBe("csrf_failed");
  expect(missing.headers()["x-crcon-csrf-recovery"]).toBe("1");
  expect(missing.headers()["cache-control"]).toContain("no-store");
  expect(
    (await (await context.request.get("/api/get_own_user_appearance")).json())
      .result.mode
  ).toBe("dark");
});
