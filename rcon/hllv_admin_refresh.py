"""Reconnect workarounds for HLL Vietnam admin groups."""

import logging
from collections.abc import Iterable

from rcon.types import AdminType, GameEnum

logger = logging.getLogger(__name__)

RECONNECT_REFRESH_ROLES = frozenset({"spectator"})


def _matching_admin(
    admins: Iterable[AdminType],
    player_id: str,
    roles: frozenset[str],
) -> AdminType | None:
    for admin in admins:
        role = str(admin.get("role") or "").lower()
        if str(admin.get("player_id") or "") == player_id and role in roles:
            return admin
    return None


def refresh_hllv_admin_role_on_connect(
    rcon,
    player_id: str,
    player_name: str,
    roles: frozenset[str] = RECONNECT_REFRESH_ROLES,
) -> bool:
    """Re-apply an existing HLLV admin group to a new player session.

    HLL Vietnam can retain an entry in ``GetAdminUsers`` while failing to
    activate the associated spectator privileges after the player reconnects.
    This workaround is deliberately additive: it never removes a role and only
    calls ``AddAdmin`` after a fresh server read confirms the assignment still
    exists.  The fresh read prevents a stale CRCON cache from resurrecting a
    role that an operator removed directly on the game server.
    """

    if rcon.config.game != GameEnum.HLL_VIETNAM or not player_id:
        return False

    # HLLV admin commands use the EOS product-user ID. Refuse to refresh a
    # classic 17-digit Steam ID accidentally stored in the HLLV admin list.
    if len(player_id) != 32:
        logger.warning(
            "Skipping HLLV admin refresh for non-EOS player ID %s", player_id
        )
        return False

    cached_admin = _matching_admin(rcon.get_admin_ids(), player_id, roles)
    if cached_admin is None:
        return False

    cache_clear = getattr(rcon.get_admin_ids, "cache_clear", None)
    if callable(cache_clear):
        cache_clear()

    live_admin = _matching_admin(rcon.get_admin_ids(), player_id, roles)
    if live_admin is None:
        logger.info(
            "Skipping HLLV admin refresh for %s: role is absent from the live admin list",
            player_id,
        )
        return False

    role = str(live_admin.get("role") or "").lower()
    description = str(live_admin.get("name") or player_name or "HLLV reconnect")
    refreshed = bool(
        rcon.add_admin(
            player_id=player_id,
            role=role,
            description=description,
        )
    )
    if refreshed:
        logger.info(
            "Refreshed HLLV %s privileges after reconnect for %s",
            role,
            player_id,
        )
    else:
        logger.warning(
            "HLLV rejected the %s privilege refresh for %s",
            role,
            player_id,
        )
    return refreshed
