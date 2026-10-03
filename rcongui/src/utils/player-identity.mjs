// HLL:V calls the secondary account ID `steam_id` even for PSN and Xbox.
// Keep it as a string and use the platform, not the field name or ID length,
// to interpret it. player_id remains the identity used for all RCON actions.
const text = (...values) =>
  values.find((value) => typeof value === "string" && value.trim())?.trim() ||
  "";

export const PLATFORM_LABELS = {
  steam: "Steam",
  epic: "Epic Games",
  xbl: "Xbox Live",
  xsx: "Xbox Series X|S",
  psn: "PlayStation Network",
  ps5: "PlayStation 5",
};

const PLATFORM_ALIASES = {
  steam: "steam",
  egs: "epic",
  epic: "epic",
  epicgames: "epic",
  xbl: "xbl",
  xboxlive: "xbl",
  xsx: "xsx",
  xboxseries: "xsx",
  xboxseriesx: "xsx",
  xboxseriess: "xsx",
  psn: "psn",
  playstationnetwork: "psn",
  ps5: "ps5",
  playstation5: "ps5",
};

export function normalizePlatform(value) {
  const name = text(value).replace(/^EPlatformFamily::/i, "");
  return PLATFORM_ALIASES[name.toLowerCase()] || name;
}

export function platformLabel(value) {
  const platform = normalizePlatform(value);
  return PLATFORM_LABELS[platform] || platform;
}

export function isSteamId(value) {
  if (typeof value !== "string" || !/^\d{17}$/.test(value)) return false;
  const id = BigInt(value);
  // Public individual SteamID64, not an arbitrary 17-digit console account.
  return id >= 76561197960265728n && id <= 76561202255233023n;
}

export function steamProfileUrl(value) {
  return isSteamId(value)
    ? `https://steamcommunity.com/profiles/${value}`
    : null;
}

function namedProfileUrl(platform, name) {
  if (!name || /[\u0000-\u001f\u007f/\\?]/u.test(name)) return null;
  try {
    if (
      ["psn", "ps5"].includes(platform) &&
      /^[a-z][a-z0-9_-]{2,15}$/i.test(name)
    ) {
      return `https://profile.playstation.com/${encodeURIComponent(name)}`;
    }
    if (["xbl", "xsx"].includes(platform) && name.length <= 32) {
      return `https://www.xbox.com/en-US/play/user/${encodeURIComponent(name)}`;
    }
  } catch {
    // Invalid Unicode must not break an entire player list.
  }
  return null;
}

export function getPlayerIdentity(value = {}) {
  const player = value || {};
  const profile = player.profile || {};
  const soldier = player.soldier || profile.soldier || {};
  const playerId = text(player.player_id, profile.player_id, player.iD);
  const rawPlatform = text(player.platform, profile.platform, soldier.platform);
  let platformId = text(
    player.platform_id,
    player.steam_id,
    player.steamId,
    profile.platform_id,
    profile.steam_id
  );
  const platform =
    normalizePlatform(rawPlatform) ||
    (isSteamId(platformId || playerId) ? "steam" : "");
  if (!platformId && platform === "steam" && isSteamId(playerId))
    platformId = playerId;
  const game = text(player.game, profile.game);
  const eosId =
    text(player.eos_id, player.eosId, profile.eos_id, soldier.eos_id) ||
    (/^[a-f0-9]{32}$/i.test(playerId) &&
    (["hll_vietnam", "hllv"].includes(game) ||
      (platform && platformId && platformId !== playerId))
      ? playerId
      : "");
  // Never turn EOS into a platform profile link, even with malformed API data.
  if (platformId === eosId) platformId = "";
  const profileName = text(
    player.psn_online_id,
    player.xbox_gamertag,
    profile.psn_online_id,
    profile.xbox_gamertag,
    player.name,
    soldier.name
  );
  const profileUrl =
    platform === "steam"
      ? steamProfileUrl(platformId)
      : namedProfileUrl(platform, profileName);
  const profileByName = Boolean(profileUrl && platform !== "steam");
  const platformIdLabel =
    {
      steam: "steamId",
      psn: "psnId",
      ps5: "psnId",
      xbl: "xboxId",
      xsx: "xboxId",
    }[platform] || "platformId";
  const identifiers = [];
  if (platformId)
    identifiers.push({
      kind: platformIdLabel,
      value: platformId,
      href: profileUrl,
    });
  if (eosId) identifiers.push({ kind: "eosId", value: eosId });
  if (playerId && playerId !== platformId && playerId !== eosId) {
    identifiers.push({ kind: "playerId", value: playerId });
  }
  return {
    platform,
    platformId,
    playerId,
    eosId,
    profileUrl,
    profileName,
    profileByName,
    identifiers,
  };
}
