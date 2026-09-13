import assert from "node:assert/strict";
import test from "node:test";
import { getMessageBody, groupLogRows } from "./log-stacks.mjs";

const body =
  "Dein Squad hat keinen Offizier. Squads ohne Squadleader sind nicht erlaubt.";
const message = (offset, overrides = {}) => ({
  action: "MESSAGE",
  timestamp_ms: 1_800_000_000_000 + offset,
  player_name_1: `Player ${offset}`,
  player_id_1: String(76561198000000000n + BigInt(offset)),
  message: `Player ${offset}(76561198000000000): ${body}`,
  sub_content: body,
  ...overrides,
});
const rows = (events) =>
  events.map((original, id) => ({ id: String(id), original }));
const sizes = (events) =>
  groupLogRows(rows(events)).map((group) => group.rows.length);

test("stacks consecutive identical MESSAGE bodies across recipients, without losing rows", () => {
  const input = rows([
    message(4),
    message(3),
    message(2),
    message(1),
    message(0),
  ]);
  input.forEach((row) => {
    Object.freeze(row.original);
    Object.freeze(row);
  });
  Object.freeze(input);
  const grouped = groupLogRows(input);
  assert.equal(grouped.length, 1);
  assert.equal(grouped[0].body, body);
  assert.deepEqual(
    grouped.flatMap((group) => group.rows),
    input
  );
});

test("only strips the exact recipient prefix, preserving names and punctuation in the body", () => {
  const event = { player_name_1: "A.[B]:", player_id_1: "76561198000000001" };
  for (const prefix of [
    "A.[B]:(76561198000000001): ",
    "A.[B]:(Axis/76561198000000001): ",
    "A.[B]:: ",
  ]) {
    assert.equal(
      getMessageBody({ ...event, message: `${prefix}Hello A.[B]:!` }),
      "Hello A.[B]:!"
    );
  }
  assert.equal(
    getMessageBody({ ...event, message: "Other: Hello A.[B]:!" }),
    "Other: Hello A.[B]:!"
  );
  assert.equal(getMessageBody({ message: body }), body);
});

test("prefers parser sub_content and never treats personalization as identical", () => {
  assert.equal(getMessageBody(message(0, { message: "Wrong prefix" })), body);
  assert.deepEqual(
    sizes([
      message(1, { sub_content: "Hi A" }),
      message(0, { sub_content: "Hi B" }),
    ]),
    [1, 1]
  );
});

test("supports older logs without sub_content", () => {
  assert.deepEqual(
    sizes([
      message(1, {
        sub_content: undefined,
        message: `Player 1(76561198000000001): ${body}`,
      }),
      message(0, { sub_content: undefined }),
    ]),
    [2]
  );
});

test("different messages and intervening events break a stack", () => {
  assert.deepEqual(
    sizes([
      message(4),
      message(3),
      message(2, { sub_content: "Different" }),
      message(1),
      message(0),
    ]),
    [2, 1, 2]
  );
  assert.deepEqual(
    sizes([message(2), message(1, { action: "KILL" }), message(0)]),
    [1, 1, 1]
  );
});

for (const action of [
  "KILL",
  "TEAM KILL",
  "CHAT[Team]",
  "ADMIN KICK",
  "MATCH START",
  "CONNECTED",
]) {
  test(`${action} events remain separate even with identical text`, () => {
    assert.deepEqual(
      sizes([message(1, { action }), message(0, { action })]),
      [1, 1]
    );
  });
}

test("limits the entire burst to 60 seconds, not just each adjacent gap", () => {
  assert.deepEqual(sizes([message(60_000), message(30_000), message(0)]), [3]);
  assert.deepEqual(
    sizes([message(60_001), message(30_000), message(0)]),
    [1, 2]
  );
});

test("keeps empty or undated messages visible individually", () => {
  for (const overrides of [
    { sub_content: "" },
    { sub_content: "  " },
    { timestamp_ms: null },
    { timestamp_ms: NaN },
    { timestamp_ms: Infinity },
    { timestamp_ms: 1e308 },
    { timestamp_ms: undefined },
  ]) {
    assert.deepEqual(
      sizes([message(1, overrides), message(0, overrides)]),
      [1, 1]
    );
  }
  assert.deepEqual(groupLogRows([]), []);
});

test("does not normalize whitespace, case or IDs in a message body for matching", () => {
  assert.deepEqual(
    sizes([
      message(3, { sub_content: "Hello" }),
      message(2, { sub_content: "hello" }),
      message(1, { sub_content: "hello " }),
      message(0, { sub_content: "hello (76561198000000000)" }),
    ]),
    [1, 1, 1, 1]
  );
});

test("preserves order in either time direction and keeps burst keys on live prepends", () => {
  const old = [message(2), message(1), message(0)];
  const descending = groupLogRows(rows(old));
  const ascending = groupLogRows(rows([...old].reverse()));
  assert.deepEqual(
    ascending[0].rows.map((row) => row.original),
    [...old].reverse()
  );
  const updated = groupLogRows(
    rows([message(4, { action: "KILL" }), message(3), ...old])
  );
  assert.equal(descending[0].key, updated[1].key);
  assert.equal(ascending[0].key, descending[0].key);
});

test("equal timestamps and exact duplicate records retain their count and stable keys", () => {
  const old = [message(0, { player_id_1: "two" }), message(0)];
  assert.equal(
    groupLogRows(rows(old))[0].key,
    groupLogRows(rows([message(0, { player_id_1: "three" }), ...old]))[0].key
  );
  assert.deepEqual(sizes([message(0), message(0), message(0)]), [3]);
  const split = groupLogRows(
    rows([message(0), message(0, { action: "KILL" }), message(0)])
  );
  assert.equal(new Set(split.map((group) => group.key)).size, 3);
});

test("only counts rows supplied by the current filtered page", () => {
  const all = rows([message(3), message(2), message(1), message(0)]);
  assert.equal(groupLogRows(all.slice(0, 2))[0].rows.length, 2);
  assert.equal(
    groupLogRows(
      all.filter((row) => row.original.player_name_1 === "Player 2")
    )[0].rows.length,
    1
  );
});

test("keeps 100 identical messages in a single stack without losing recipients", () => {
  const events = Array.from({ length: 100 }, (_, index) =>
    message((99 - index) * 100)
  );
  const groups = groupLogRows(rows(events));
  assert.equal(groups.length, 1);
  assert.equal(groups[0].rows.length, 100);
  assert.deepEqual(
    groups[0].rows.map((row) => row.original),
    events
  );
});
