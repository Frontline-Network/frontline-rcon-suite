import test from "node:test";
import assert from "node:assert/strict";
import { passwordRequest } from "./password-client.mjs";

test("passwords are sent once in an allowlisted POST body with explicit CSRF", async () => {
  const result = await passwordRequest(
    {
      language: "de",
      csrfToken: "csrf-test",
      values: {
        old_password: "old",
        new_password1: "new",
        new_password2: "new",
        user_id: "another-user",
      },
    },
    async (url, options) => {
      assert.equal(url, "/accounts/password_change/?ui_language=de");
      assert.equal(options.method, "POST");
      assert.equal(options.headers["X-CSRFToken"], "csrf-test");
      assert.equal(options.cache, "no-store");
      assert.equal(options.credentials, "same-origin");
      assert.deepEqual(Object.fromEntries(options.body), {
        old_password: "old",
        new_password1: "new",
        new_password2: "new",
      });
      return { ok: true, status: 200, json: async () => ({ changed: true }) };
    }
  );
  assert.equal(result.data.changed, true);
});

test("missing CSRF token prevents sending secrets", async () => {
  await assert.rejects(
    passwordRequest({ values: { new_password1: "secret" } }, () => {
      assert.fail("No request should be sent");
    }),
    /CSRF/
  );
});

test("HTML responses never become a successful password change", async () => {
  const result = await passwordRequest({ language: "en" }, async () => ({
    ok: true,
    status: 200,
    json: async () => {
      throw new Error("HTML");
    },
  }));
  assert.equal(result.data, null);
});

test("reset uses the token-free session route and excludes old passwords", async () => {
  await passwordRequest(
    {
      mode: "reset",
      uid: "MjE",
      csrfToken: "csrf",
      values: {
        new_password1: "new",
        new_password2: "new",
        old_password: "old",
        token: "private",
      },
    },
    async (url, options) => {
      assert.equal(url, "/accounts/reset/MjE/set-password/?ui_language=en");
      assert.deepEqual(Object.keys(Object.fromEntries(options.body)), [
        "new_password1",
        "new_password2",
      ]);
      return { ok: true, status: 200, json: async () => ({ changed: true }) };
    }
  );
});

test("recovery errors are returned without retrying email requests", async () => {
  let calls = 0;
  const result = await passwordRequest(
    {
      mode: "request",
      csrfToken: "csrf",
      values: { email: "test@example.test" },
    },
    async (url, options) => {
      calls += 1;
      assert.equal(url, "/accounts/password_reset/?ui_language=en");
      assert.deepEqual(Object.fromEntries(options.body), {
        email: "test@example.test",
      });
      return {
        ok: false,
        status: 429,
        json: async () => ({ error: "rate_limited" }),
      };
    }
  );
  assert.equal(calls, 1);
  assert.equal(result.status, 429);
});
