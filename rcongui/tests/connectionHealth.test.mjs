import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const sourceUrl = new URL("../src/utils/connectionHealth.js", import.meta.url);
const source = await readFile(sourceUrl, "utf8");
const moduleUrl = `data:text/javascript;base64,${Buffer.from(source).toString(
  "base64"
)}`;
const { CONNECTION_STATE, createConnectionHealth, isUsableConnectionState } =
  await import(moduleUrl);

test("reports an initial request as loading", () => {
  const health = createConnectionHealth({ isPending: true });

  assert.equal(health.state, CONNECTION_STATE.LOADING);
  assert.equal(health.lastSuccessAt, null);
});

test("reports successful current data as online", () => {
  const health = createConnectionHealth({
    data: { name: "Server 3" },
    dataUpdatedAt: 1234,
    isFetching: false,
  });

  assert.equal(health.state, CONNECTION_STATE.ONLINE);
  assert.equal(health.lastSuccessAt, 1234);
  assert.equal(isUsableConnectionState(health.state), true);
});

test("never presents cached data as current after a failed refresh", () => {
  const health = createConnectionHealth({
    data: { name: "Server 3" },
    dataUpdatedAt: 1234,
    errorUpdatedAt: 2345,
    isError: true,
  });

  assert.equal(health.state, CONNECTION_STATE.STALE);
  assert.equal(health.lastAttemptAt, 2345);
  assert.equal(isUsableConnectionState(health.state), true);
});

test("reports a failed request without cached data as offline", () => {
  const health = createConnectionHealth({
    data: undefined,
    errorUpdatedAt: 2345,
    isError: true,
  });

  assert.equal(health.state, CONNECTION_STATE.OFFLINE);
});

test("reports dependent data as unknown or stale while CRCON is unavailable", () => {
  assert.equal(
    createConnectionHealth({ data: undefined }, { enabled: false }).state,
    CONNECTION_STATE.UNKNOWN
  );
  assert.equal(
    createConnectionHealth({ data: { map: "old" } }, { enabled: false }).state,
    CONNECTION_STATE.STALE
  );
});

test("marks background refreshes without changing the online state", () => {
  const health = createConnectionHealth({
    data: { name: "Server 3" },
    dataUpdatedAt: 1234,
    isFetching: true,
  });

  assert.equal(health.state, CONNECTION_STATE.ONLINE);
  assert.equal(health.isRefreshing, true);
});
