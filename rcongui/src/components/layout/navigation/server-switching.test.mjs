import assert from "node:assert/strict";
import test from "node:test";

import {
  buildServerOptions,
  getServerHref,
  getServerShortCode,
} from "./server-switching.mjs";

test("server switching preserves the current workspace, query and hash", () => {
  assert.equal(
    getServerHref(
      { link: "https://rcon2.example.test" },
      "https://rcon1.example.test/settings/maps?tab=pool#active"
    ),
    "https://rcon2.example.test/settings/maps?tab=pool#active"
  );
  assert.equal(
    getServerHref(
      { port: 3004 },
      "http://127.0.0.1:3001/views/live?team=all#players"
    ),
    "http://127.0.0.1:3004/views/live?team=all#players"
  );
});

test("server switching deduplicates targets and keeps the current server first", () => {
  const current = { server_number: 2, name: "Current" };
  const result = buildServerOptions(current, [
    { server_number: 3, name: "Third" },
    { server_number: 2, name: "Duplicate" },
    { server_number: 1, name: "First" },
  ]);

  assert.deepEqual(
    result.map((server) => server.server_number),
    [2, 1, 3]
  );
  assert.equal(getServerShortCode(current), "S2");
  assert.equal(getServerShortCode(null), "S–");
});
