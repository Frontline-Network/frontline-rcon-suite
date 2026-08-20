# Game-profile status contract

The authenticated `get_status` response carries the current game identity and
the modes supported by the active server profile. This keeps the persistent
administrator context truthful even when a user may view server status but
does not have the separate `can_view_connection_info` permission.

## Fields

- `game` is `hll` for Hell Let Loose or `hllv` for Hell Let Loose: Vietnam.
- `supported_game_modes` is derived from the active `GameProfile`; it is not a
  frontend-maintained list.
- Existing status fields remain unchanged.

The frontend already normalizes `hllv`, `hll_vietnam`, and `vietnam` to the
same HLL: Vietnam presentation. Consumers must treat an absent field from an
older CRCON installation as unknown rather than assuming Hell Let Loose.

## Compatibility evidence

The paired profile test verifies both games and proves that a mode from one
profile does not leak into the other. In particular, HLL exposes its small
game modes while HLL: Vietnam exposes Domination and does not claim Skirmish.

This contract is the source for later compatibility labels in settings,
Automods, map controls, and action confirmations. It deliberately reports only
profile-backed facts; it does not claim that a feature is supported merely
because a similarly named frontend route exists.
