import { test } from "node:test";
import assert from "node:assert/strict";
import { loadThemeWithRetry } from "./load-theme.mjs";
test("a transient theme failure gets one retry", async () => {
  let calls = 0;
  assert.equal(
    await loadThemeWithRetry(async () => {
      if (++calls === 1) throw Error();
      return "theme";
    }),
    "theme"
  );
  assert.equal(calls, 2);
});
test("permanent failure terminates instead of looping", async () => {
  let calls = 0;
  await assert.rejects(
    loadThemeWithRetry(async () => {
      calls++;
      throw Error();
    })
  );
  assert.equal(calls, 2);
});
test("an obsolete theme selection is not retried", async () => {
  let calls = 0;
  await assert.rejects(
    loadThemeWithRetry(
      async () => {
        calls++;
        throw Error();
      },
      () => false
    )
  );
  assert.equal(calls, 1);
});
