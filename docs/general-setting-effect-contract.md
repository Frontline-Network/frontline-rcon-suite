# General setting-effect contract

Status: API foundation. The existing cards do not consume this response yet;
their visible integration remains gated on current signed-in RCON3 screenshots
at 390, 768 and 1440 px.

## Why this exists

The current general-settings page reads one flat `get_server_settings` object.
It cannot distinguish a missing permission from an unreachable game server,
does not know whether Auto Settings may overwrite a value, and has no reliable
audit provenance. The frontend therefore cannot explain the difference between
the value it just read, a recommended value and the value an automation may
apply later.

`get_general_setting_effects` adds a versioned, read-only contract. It does not
change a game-server setting, start a service, add polling or replace the stable
legacy endpoint.

## Truth rules

- Each setting is read separately, so one unavailable command produces a
  partial result instead of erasing every other value.
- A user without a view permission receives `permission_missing`; the getter is
  never called and its value is never exposed.
- `read_at` is the time CRCON assembled the response. Because several RCON
  getters use a cache without an origin timestamp, freshness remains `unknown`.
  The API does not pretend this is the last successful game-server refresh.
- Direct game-server settings use the observed RCON value for both configured
  and effective state. Auto Settings candidates are reported separately and
  are never described as active without a simulation context.
- Protocol defaults remain `unknown` unless they are documented. Recommended
  Frontline values are a separate field.
- Raw RCON, Redis, database and transport errors are never returned.
- Audit provenance is only returned with `can_view_audit_logs`. The contract
  distinguishes the last attempt from the last successful change.

## State matrix

The top-level response reports `health` (`available`, `partial`, `unavailable`
or `unknown`) independently from permission `visibility` (`full`, `partial` or
`none`). Each setting includes:

- configured and effective value state;
- default and recommended value state;
- unit, immediate activation and side-effect codes;
- HLL/HLL Vietnam compatibility;
- change and restore permissions;
- Auto Settings candidates and conflict codes;
- last attempt and last successful change when audit access is allowed;
- a machine-readable next action for unavailable or permission-blocked data.

This is intentionally machine-readable. The later UI slice must translate all
codes and reuse the existing Frontline cards after current screenshots establish
the visual source of truth.

## Resource behavior

The endpoint performs no work until explicitly requested. One request executes
only the individually permitted setting getters, at most one Auto Settings read
and one windowed audit query. It introduces no timer, worker, cache refresh or
background request.

## Automated evidence

- Thirteen focused contract tests cover metadata completeness, JSON
  serialisation, HLL/HLLV/unknown-game compatibility, full/partial/no
  visibility, partial RCON failure, sanitisation, Auto Settings candidates,
  audit outcomes, restoration and permission combinations.
- The adjacent Auto Settings, cache, game-profile and multi-server suites pass
  together with the new contract (88 tests in the focused matrix).
- Django's test configuration imports the endpoint list with exactly one
  `get_general_setting_effects` registration.
- The existing full Linux CI suite remains the merge gate. The Windows-only
  local full-suite run needs its PostgreSQL service and clean per-test Redis
  state and is therefore not used as completion evidence.
