import assert from "node:assert/strict";
import { test } from "node:test";
import {
  getPlayerIdentity,
  isSteamId,
  normalizePlatform,
  platformLabel,
  steamProfileUrl,
} from "./player-identity.mjs";

const eos = "00000000000000000000000000000001";
const steam = "76561198000000001";
const psn = "1234567890123456789";
const xuid = "2533274800000001";

test("normalizes live enums, case, whitespace and legacy platform values", () => {
  for (const [input, canonical, label] of [
    [" EPlatformFamily::Steam ", "steam", "Steam"],
    ["EPlatformFamily::PS5", "ps5", "PlayStation 5"],
    ["EPlatformFamily::XboxSeries", "xsx", "Xbox Series X|S"],
    ["EPlatformFamily::EGS", "epic", "Epic Games"],
    ["STEAM", "steam", "Steam"],
    ["psn", "psn", "PlayStation Network"],
    ["xbl", "xbl", "Xbox Live"],
    ["xsx", "xsx", "Xbox Series X|S"],
  ]) {
    assert.equal(normalizePlatform(input), canonical);
    assert.equal(platformLabel(input), label);
  }
  assert.equal(
    platformLabel("EPlatformFamily::FuturePlatform"),
    "FuturePlatform"
  );
  assert.equal(normalizePlatform(null), "");
});

test("HLLV Steam uses the secondary ID for the link, never EOS", () => {
  const identity = getPlayerIdentity({
    player_id: eos,
    eos_id: eos,
    steam_id: steam,
    platform: "EPlatformFamily::Steam",
  });
  assert.equal(identity.playerId, eos);
  assert.equal(
    identity.profileUrl,
    `https://steamcommunity.com/profiles/${steam}`
  );
  assert.deepEqual(identity.identifiers, [
    { kind: "steamId", value: steam, href: identity.profileUrl },
    { kind: "eosId", value: eos },
  ]);
});

test("legacy HLL Steam IDs need no duplicate row or platform metadata", () => {
  const identity = getPlayerIdentity({ player_id: steam });
  assert.equal(identity.platform, "steam");
  assert.equal(identity.identifiers.length, 1);
  assert.equal(identity.eosId, "");
  assert.equal(identity.platformId, steam);
});

test("PS5 labels the misleading steam_id field and keeps all 19 digits", () => {
  const identity = getPlayerIdentity({
    player_id: eos,
    steam_id: psn,
    platform: "EPlatformFamily::PS5",
    name: "Player_Test",
  });
  assert.equal(identity.identifiers[0].kind, "psnId");
  assert.equal(identity.platformId, psn);
  assert.equal(
    identity.profileUrl,
    "https://profile.playstation.com/Player_Test"
  );
  assert.equal(identity.profileByName, true);
  assert.equal(identity.identifiers[1].href, undefined);
});

test("Xbox uses an encoded gamertag, not XUID or EOS as a profile name", () => {
  const identity = getPlayerIdentity({
    player_id: eos,
    steam_id: xuid,
    platform: "EPlatformFamily::XboxSeries",
    name: "Player One#1234",
  });
  assert.equal(identity.identifiers[0].kind, "xboxId");
  assert.equal(
    identity.profileUrl,
    "https://www.xbox.com/en-US/play/user/Player%20One%231234"
  );
  assert.equal(identity.profileByName, true);
  assert.equal(identity.platformId, xuid);
});

test("offline profiles use stored platform and soldier name, never admin account aliases", () => {
  const identity = getPlayerIdentity({
    player_id: eos,
    steam_id: psn,
    account: { name: "WrongProfile" },
    soldier: { platform: "ps5", name: "CorrectProfile", eos_id: eos },
  });
  assert.equal(
    identity.profileUrl,
    "https://profile.playstation.com/CorrectProfile"
  );
  assert.equal(
    getPlayerIdentity({
      player_id: eos,
      profile: { steam_id: steam, soldier: { platform: "steam", eos_id: eos } },
    }).platformId,
    steam
  );
});

test("live identity fields take precedence over stored profile data", () => {
  const identity = getPlayerIdentity({
    player_id: eos,
    platform: "PS5",
    platform_id: psn,
    name: "CurrentName",
    profile: {
      steam_id: steam,
      soldier: { platform: "steam", name: "OldName" },
    },
  });
  assert.equal(identity.platformId, psn);
  assert.equal(identity.profileName, "CurrentName");
  assert.equal(
    identity.profileUrl,
    "https://profile.playstation.com/CurrentName"
  );
});

test("Epic compound IDs stay intact and have no invented public profile link", () => {
  const compound = `${"a".repeat(32)}|${eos}`;
  const identity = getPlayerIdentity({
    player_id: eos,
    steam_id: compound,
    platform: "EPlatformFamily::EGS",
  });
  assert.equal(identity.platformId, compound);
  assert.equal(identity.identifiers[0].kind, "platformId");
  assert.equal(identity.profileUrl, null);
});

test("unknown platforms and GUIDs are never guessed to be Xbox", () => {
  for (const player of [
    null,
    {},
    { player_id: eos, name: "Player" },
    { player_id: "12345678901234567", name: "Player" },
  ]) {
    assert.equal(getPlayerIdentity(player).profileUrl, null);
    assert.notEqual(getPlayerIdentity(player).platform, "xbl");
  }
  const unknown = getPlayerIdentity({
    player_id: eos,
    steam_id: steam,
    platform: "EPlatformFamily::FuturePlatform",
  });
  assert.equal(unknown.platform, "FuturePlatform");
  assert.equal(unknown.profileUrl, null);
});

test("missing or malformed platform IDs cannot turn EOS into Steam links", () => {
  for (const secondary of [
    undefined,
    eos,
    "not-an-id",
    "12345678901234567",
    Number(steam),
  ]) {
    const identity = getPlayerIdentity({
      player_id: eos,
      eos_id: eos,
      steam_id: secondary,
      platform: "steam",
    });
    assert.equal(identity.profileUrl, null);
    assert.equal(
      identity.identifiers.find((row) => row.kind === "eosId").href,
      undefined
    );
  }
  for (const value of [
    null,
    undefined,
    76561198000000001,
    "12345678901234567",
    eos,
    `${steam}/evil`,
  ]) {
    assert.equal(isSteamId(value), false);
    assert.equal(steamProfileUrl(value), null);
  }
});

test("invalid or unavailable console names keep IDs copyable without unsafe links", () => {
  for (const platform of ["ps5", "xsx"]) {
    for (const name of [
      "",
      "http://attacker.test",
      "a/b",
      "../test",
      "test?query",
      "test\nname",
      "\ud800",
    ]) {
      const identity = getPlayerIdentity({ platform, name, steam_id: psn });
      assert.equal(identity.profileUrl, null, `${platform}: ${name}`);
      assert.equal(identity.platformId, psn);
    }
  }
});

test("raw payload aliases and historical HLLV without soldier EOS still work", () => {
  assert.equal(
    getPlayerIdentity({
      iD: eos,
      steamId: steam,
      platform: "EPlatformFamily::Steam",
    }).profileUrl,
    steamProfileUrl(steam)
  );
  const identity = getPlayerIdentity({ player_id: eos, game: "hll_vietnam" });
  assert.deepEqual(identity.identifiers, [{ kind: "eosId", value: eos }]);
});
