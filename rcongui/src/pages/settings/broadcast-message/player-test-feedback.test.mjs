import test from "node:test";
import assert from "node:assert/strict";
import { playerTestErrorKey } from "./player-test-feedback.mjs";

test("distinguishes a rejection from a possibly delivered test message", () => {
  assert.equal(playerTestErrorKey("RCON rejected the player message"), "settings.campaigns.playerTestRejected");
  assert.equal(playerTestErrorKey("Message delivery could not be confirmed; it may have been delivered"), "settings.campaigns.playerTestUnconfirmed");
  assert.equal(playerTestErrorKey("other failure"), null);
});
