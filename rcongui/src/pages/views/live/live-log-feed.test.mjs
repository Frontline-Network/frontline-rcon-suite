import { test } from "node:test";
import assert from "node:assert/strict";
import { mergeLogPage, LIVE_LOG_GC_TIME } from "./live-log-feed.mjs";
const row = (id) => ({ cursor_id: id, timestamp_ms: 1, message: id });
const page = (ids, rest = {}) => ({
  logs: ids.map(row),
  actions: ["CHAT"],
  players: ["P"],
  newest: ids[0],
  oldest: ids.at(-1),
  has_older: true,
  reset: null,
  ...rest,
});
test("same-timestamp events are merged by identity and duplicates removed", () => {
  const old = page(["b", "c"]);
  const merged = mergeLogPage(old, page(["a", "b"]), "newer", 3);
  assert.deepEqual(
    merged.logs.map((r) => r.cursor_id),
    ["a", "b", "c"]
  );
  assert.equal(merged.newest, "a");
  assert.equal(merged.oldest, "c");
});
test("older pages preserve the live cursor and enforce the memory limit", () => {
  const merged = mergeLogPage(
    page(["a", "b"]),
    page(["b", "c", "d"]),
    "older",
    3
  );
  assert.equal(merged.newest, "a");
  assert.equal(merged.logs.length, 3);
  assert.ok(LIVE_LOG_GC_TIME <= 60_000);
});
test("empty filtered pages still move the older cursor", () => {
  const merged = mergeLogPage(
    page(["a"]),
    page([], { oldest: "z", has_older: false }),
    "older",
    50
  );
  assert.equal(merged.oldest, "z");
  assert.equal(merged.has_older, false);
});
test("expired cursors replace the old window and retain a visible notice", () => {
  const merged = mergeLogPage(
    page(["a"]),
    page(["z"], { reset: "cursor_expired" }),
    "newer",
    5
  );
  assert.deepEqual(
    merged.logs.map((r) => r.cursor_id),
    ["z"]
  );
  assert.equal(
    mergeLogPage(merged, page([], { newest: "z" }), "newer", 5).reset,
    "cursor_expired"
  );
});
test("invalid responses cannot erase loaded messages", () => {
  assert.throws(() => mergeLogPage(page(["a"]), { logs: [] }, "newer", 5));
});
