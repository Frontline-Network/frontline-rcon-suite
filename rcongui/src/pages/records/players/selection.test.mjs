import assert from "node:assert/strict";
import test from "node:test";
import { recordRecipient, selectRecordPage, toggleRecordSelection } from "./selection.mjs";

const record = (id, name = id) => ({
  player_id: id, account: { name }, names: [{ name }],
  sessions: Array(100).fill({ start: "2026-01-01" }),
  received_actions: Array(100).fill({ reason: "history" }),
  identity: { linked_accounts: [{ player_id: "another-game-account" }] },
});

test("selected recipients retain exact game IDs and labels without profile histories", () => {
  for (const id of ["76561198000000001", "0002abcdef0123456789abcdef0123456"]) {
    const player = record(id, "Chosen player");
    const recipient = recordRecipient(player);
    assert.deepEqual(recipient, {
      player_id: id, name: "Chosen player", player_name: "Chosen player",
      names: [{ name: "Chosen player" }],
    });
    assert.notEqual(recipient.names, player.names);
  }
});

test("page selection retains only selected recipients and drops deselected profiles", () => {
  const original = new Map();
  let selected = toggleRecordSelection(original, record("first", "First page"));
  selected = selectRecordPage(selected, [record("second", "Second page"), record("third")]);
  assert.equal(original.size, 0);
  assert.deepEqual([...selected.keys()], ["first", "second", "third"]);
  assert.equal(selected.get("first").name, "First page");
  assert.ok([...selected.values()].every((player) => !('sessions' in player) && !('received_actions' in player)));
  selected = toggleRecordSelection(selected, record("first"));
  assert.deepEqual([...selected.keys()], ["second", "third"]);
  selected = new Map(); // Same operation used by "Unselect all".
  assert.equal(selected.size, 0);
});

test("repeated selection updates replace metadata without accumulating aliases or histories", () => {
  let selected = new Map();
  for (let page = 0; page < 1000; page++) {
    selected = selectRecordPage(selected, [record("same-id", `Latest ${page}`)]);
  }
  assert.equal(selected.size, 1);
  assert.equal(selected.get("same-id").name, "Latest 999");
  assert.equal(selected.get("same-id").names.length, 1);
});

test("missing names fall back to the account ID", () => {
  assert.equal(recordRecipient({ player_id: "eos-id" }).name, "eos-id");
});
