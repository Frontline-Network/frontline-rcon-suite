const isActiveBlacklist = (record) => record?.is_active === true;

/**
 * Build a display-only summary of restrictions that still exist.
 *
 * Names are never used for matching. Linked accounts have already been
 * resolved by the backend through the authoritative Steam64 bridge. This
 * helper does not execute or transfer a ban.
 */
export const getActiveBanStatus = (player, gameServerBans = []) => {
  const bannedIds = new Set(
    gameServerBans.map((ban) => ban?.player_id).filter(Boolean)
  );
  const details = [];
  const profile = player?.profile ?? {};

  if (bannedIds.has(player?.player_id)) {
    details.push({ type: "gameServer", scope: "direct" });
  }

  (profile.blacklists ?? []).filter(isActiveBlacklist).forEach((record) => {
    details.push({ type: "blacklist", scope: "direct", record });
  });

  (profile.identity?.linked_accounts ?? []).forEach((account) => {
    if (bannedIds.has(account.player_id)) {
      details.push({ type: "gameServer", scope: "linked", account });
    }

    const existingBlacklists =
      account.existing_blacklists ?? account.active_blacklists ?? [];
    existingBlacklists.filter(isActiveBlacklist).forEach((record) => {
      details.push({ type: "blacklist", scope: "linked", account, record });
    });
  });

  return {
    isActive: details.length > 0,
    details,
  };
};
