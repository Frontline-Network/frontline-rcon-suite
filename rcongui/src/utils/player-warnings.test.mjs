import assert from "node:assert/strict";
import test from "node:test";
import {
  countRecentWarnings,
  hasRecentWarnings,
  isInformationalPlayerMessage,
} from "./player-warnings.mjs";

const now = Date.parse("2026-09-13T12:00:00Z");
const action = (overrides = {}) => ({
  action_type: "MESSAGE",
  by: "Frontline Admin",
  reason: "Bitte beachte die Serverregeln.",
  time: "2026-09-13T11:00:00Z",
  ...overrides,
});

test("campaign and VIP messages do not mark their recipients as warned", () => {
  for (const by of [
    "Campaign: Mic-Pflicht DE",
    "Campaign: Mic-Pflicht EN",
    "Campaign: 42",
    "VIP lifecycle: unverified",
    "VIP lifecycle: expiring",
    "VIP lifecycle test: expired",
  ]) {
    const messages = [action({ by })];
    assert.equal(isInformationalPlayerMessage(messages[0]), true);
    assert.equal(countRecentWarnings(messages, now), 0);
    assert.equal(hasRecentWarnings(messages, now), false);
  }
});

test("100 campaign messages stay in the history without adding warnings", () => {
  const messages = Object.freeze(
    Array.from({ length: 100 }, () =>
      Object.freeze(action({ by: "Campaign: Mic-Pflicht DE" }))
    )
  );
  const original = JSON.stringify(messages);
  assert.equal(countRecentWarnings(messages, now), 0);
  assert.equal(hasRecentWarnings(messages, now), false);
  assert.equal(JSON.stringify(messages), original);
});

test("manual and automod warnings are preserved, including in mixed histories", () => {
  const messages = [
    action({ by: "Campaign: Mic-Pflicht DE" }),
    action({ by: "VIP lifecycle: unverified" }),
    action(),
    action({ by: "AUTOMOD_NO_LEADER" }),
  ];
  assert.equal(countRecentWarnings(messages, now), 2);
  assert.equal(hasRecentWarnings(messages, now), true);
});

test("sender exclusions only apply to messages, not punishments or bans", () => {
  for (const action_type of ["PUNISH", "KICK", "TEMPBAN", "PERMABAN"]) {
    const messages = [action({ action_type, by: "Campaign: Admin" })];
    assert.equal(isInformationalPlayerMessage(messages[0]), false);
    assert.equal(countRecentWarnings(messages, now), 1);
    assert.equal(hasRecentWarnings(messages, now), true);
  }
});

test("message text and merely similar sender names cannot hide warnings", () => {
  for (const by of [
    "Admin Campaign: test",
    "CampaignAdmin",
    "VIP lifecycle Admin",
    "",
    null,
  ]) {
    const messages = [action({ by, reason: "Campaign: Mic-Pflicht DE" })];
    assert.equal(countRecentWarnings(messages, now), 1);
  }
});

test("the rolling 24-hour window handles timestamp offsets and its boundary", () => {
  const messages = [
    action({ time: "2026-09-12T11:59:59Z" }),
    action({ time: "2026-09-12T12:00:00Z" }),
    action({ time: "2026-09-12T12:00:01Z" }),
    action({ time: "2026-09-12T14:30:00+02:00" }),
    action({ time: "2026-09-12T13:30:00+02:00" }),
  ];
  assert.equal(countRecentWarnings(messages, now), 2);
  assert.equal(hasRecentWarnings(messages.slice(0, 2), now), false);
});

test("missing histories and invalid timestamps do not break the live view", () => {
  for (const messages of [
    undefined,
    null,
    {},
    [],
    [null, {}, action({ time: "invalid" })],
  ]) {
    assert.equal(countRecentWarnings(messages, now), 0);
    assert.equal(hasRecentWarnings(messages, now), false);
  }
});
