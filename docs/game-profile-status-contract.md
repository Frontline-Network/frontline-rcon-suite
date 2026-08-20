# Game-profile status contract

The authenticated `get_status` response carries the current game identity and
the modes supported by the active server profile. This keeps the persistent
administrator context truthful even when a user may view server status but
does not have the separate `can_view_connection_info` permission.

## Fields

- `game` is `hll` for Hell Let Loose or `hllv` for Hell Let Loose: Vietnam.
- `supported_game_modes` is derived from the active `GameProfile`; it is not a
  frontend-maintained list.
- `game_capabilities.match_timer_modes` and `warmup_timer_modes` describe the
  narrower command support documented by the RCON protocol. A supported game
  mode is not automatically a supported timer mode.
- Existing status fields remain unchanged.

The frontend already normalizes `hllv`, `hll_vietnam`, and `vietnam` to the
same HLL: Vietnam presentation. Consumers must treat an absent field from an
older CRCON installation as unknown rather than assuming Hell Let Loose.

## Compatibility evidence

The paired profile test verifies both games and proves that a mode from one
profile does not leak into the other. In particular, HLL exposes its small
game modes while HLL: Vietnam exposes Domination and does not claim Skirmish.

The HLL Vietnam RCON protocol (pages 31-32) limits custom match timers to
Warfare, Offensive, and Skirmish and warm-up timers to Warfare and Skirmish.
The active profile is intersected with those protocol limits. HLLV therefore
offers Warfare and Offensive match timers plus the Warfare warm-up timer; it
does not expose the invalid Skirmish controls or invent timer support for
Conquest and Domination. The frontend consumes the backend declaration and
keeps a conservative HLLV fallback for version-skewed installations.

This contract is the source for compatibility labels in settings, Automods,
map controls, and action confirmations. It deliberately reports only
profile- and protocol-backed facts; it does not claim that a feature is
supported merely because a similarly named frontend route exists.
