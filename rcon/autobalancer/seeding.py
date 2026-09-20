"""Conservative, read-only protection of the configured seeding population."""

import logging

from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig

logger = logging.getLogger(__name__)
SEEDING_ACTIVE = "Seeding ist aktiv: kein automatischer Teamausgleich"
SEEDING_UNKNOWN = "Seeding-Status konnte nicht sicher gelesen werden"


def seeding_active(config: AutoModSeedingUserConfig, player_count: int) -> bool:
    if not config.enabled:
        return False
    # Also protect the population below enforcement minima: turning punishments
    # off for very few players does not mean the server has finished seeding.
    limits = [
        rule.max_players
        for rule, configured in (
            (config.enforce_cap_fight, True),
            (config.disallowed_roles, bool(config.disallowed_roles.roles)),
            (config.disallowed_weapons, bool(config.disallowed_weapons.weapons)),
        )
        if rule.enabled and configured
    ]
    # Seeding rules themselves stop at >= max_players. Do not reuse the older
    # campaign helper, which ignores rule.enabled and has different boundaries.
    return bool(limits) and player_count < max(limits)


def read_seeding_active(player_count: int) -> bool | None:
    try:
        return seeding_active(AutoModSeedingUserConfig.load_from_db(), player_count)
    except Exception:
        logger.exception("Unable to read seeding protection for autobalancer")
        return None  # Unknown is blocked, never permission to switch.


def block_reason(active: bool | None) -> str | None:
    return SEEDING_UNKNOWN if active is None else SEEDING_ACTIVE if active else None
