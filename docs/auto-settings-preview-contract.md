# Auto Settings preview contract

`preview_auto_settings` validates and simulates an Auto Settings document without
calling the game server. It is the authoritative contract for the planned Basic
rule builder and remains useful to Advanced/JSON clients.

## Safety invariant

The preview module is pure: it does not import the RCON API, open a connection,
write user configuration, restart a service, or emit an audit action. All values
used by the simulation are explicit request data. Missing scenario data remains
unknown rather than being replaced by sample or cached values.

## Request

- Method: `POST`
- Command: `preview_auto_settings`
- Permission: `api.can_view_auto_settings`
- Content type: `application/json`

```json
{
  "settings": {
    "always_apply_defaults": false,
    "can_invoke_multiple_rules": false,
    "defaults": {},
    "rules": []
  },
  "scenario": {
    "player_count": 42,
    "online_mods": 1,
    "ingame_mods": 1,
    "current_map": "carentan_warfare",
    "time_of_day": "20:30"
  },
  "known_map_ids": ["carentan_warfare"]
}
```

`known_map_ids` should come from `get_maps` for the currently selected server.
This makes map compatibility specific to that installation's HLL or HLL Vietnam
profile instead of relying on a hard-coded cross-game list.

## Response

The result contains:

- `valid`: structural validity of the configuration;
- `simulation_complete`: whether every condition had enough scenario data;
- `errors`: blocking issues with stable `code`, JSON-like `path`, and details;
- `warnings`: duplicate maps, unavailable maps, and overlapping rule commands;
- `rules`: rule priority, condition outcomes, match state, and command names;
- `matched_rule_indexes`: the rules that would run in execution order;
- `effective_commands`: the final command values after defaults and rule
  precedence are applied.

`effective_commands` is empty when the simulation is incomplete. A client must
not portray missing scenario data as a real match or effective server value.

## Supported conditions

- `player_count`
- `online_mods`
- `ingame_mods`
- `current_map`
- `time_of_day`, including ranges that cross midnight

The optional `not` flag is applied after evaluating a condition. Unknown
conditions are blocking validation errors rather than silently ignored preview
results.

## Current limits

This contract does not execute or persist a configuration and does not claim to
show live server state. The form-based Basic editor, translated issue messages,
live context controls, and before/after screenshots remain separate UI work.
