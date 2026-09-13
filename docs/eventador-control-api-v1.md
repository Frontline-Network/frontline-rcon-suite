# Eventador control API v1

Tracking: [frontline-rcon-suite #246](https://github.com/Frontline-Network/frontline-rcon-suite/issues/246)
and [Eventador #104](https://github.com/pingu420-lab/Eventador/issues/104).

The private `/api/eventador/v1/` interface lets Eventador execute one frozen,
owner-approved match workflow without exposing a generic RCON proxy. It is
available for the `hll` and `hllv` game profiles and contains only these
actions: `observe`, `broadcast`, `message_players`, `set_map`,
`restart_round`, `switch_players` and `set_pause`.

## Authentication and network boundary

Every request needs a revocable `DjangoAPIKey` whose user has only
`api.can_control_eventador_events`. Browser sessions and mobile tokens are not
accepted. The Eventador worker stores the bearer value in a root-owned secret
file; it never sends a credential in a plan, URL, log or result.

Provision the identity from an existing root-owned secret file after migration:

```text
python manage.py provision_eventador_control_identity \
  --key-file /run/secrets/eventador_control_api_key
```

Rotation requires the additional `--rotate` flag. The command resets staff,
superuser, group and unrelated direct permissions, stores only the existing
one-way API-key hash and never prints the key. Requests also re-check that exact
permission scope, so later privilege drift fails closed.

Expose the API listener only on the fixed private WireGuard peer used by
Eventador. Do not publish or reverse-proxy these paths on the public CRCON
hostname. The four route groups have their own bearer-aware rate limits.

Both sides default to disabled. CRCON accepts execution only when the exact
lowercase value below is present:

```text
EVENTADOR_CONTROL_ENABLED=true
```

Any missing, uppercase or otherwise different value keeps preparation and
execution disabled. Capability and state reads stay available to the dedicated
identity so a disabled deployment can be checked safely.

## Routes

| Method | Path | Command |
| --- | --- | --- |
| `GET` | `/api/eventador/v1/capabilities` | `get_eventador_control_capabilities` |
| `GET` | `/api/eventador/v1/state` | `get_eventador_control_state` |
| `POST` | `/api/eventador/v1/steps/prepare` | `prepare_eventador_control_step` |
| `POST` | `/api/eventador/v1/steps/{preparation_id}/execute` | `execute_eventador_control_step` |
| `GET` | `/api/eventador/v1/results/{idempotency_key}` | `get_eventador_control_result` |

Responses use the existing seven-key CRCON envelope. The v1 result objects are
strict: consumers must reject extra or missing keys.

## Prepare and execute

The prepare payload binds schema version, Eventador event ID and published
revision, workflow revision, step ID, UUIDv4 idempotency key, execution time,
server number, game profile, action, reason, arguments and expected state. The
expected state contains map, round hash, roster hash, observation time and the
previous step ID.

Preparation fails closed when the observation is older than 30 seconds, the
server or game differs, the map or roster changed, a player is absent, a player
is already on the requested side, the map ID is unsupported, a previous step
did not succeed, or another step in the workflow uses a different event
revision. A conflict is stored as a terminal receipt and can be retrieved by
the idempotency key.

A valid preparation expires after 300 seconds. Its confirmation token is an
HMAC derived from the server secret, preparation ID and frozen-plan digest; no
plaintext confirmation capability is stored. Execute locks and marks the
receipt before the first game command. A process crash or uncertain RCON reply
therefore becomes `unknown` and is never replayed. A repeated request returns
the stored receipt.

Preparation accepts only execution times from 30 seconds in the past through
300 seconds in the future. Execute remains closed until five seconds before the
bound time and expires 30 seconds after it. A layer must resolve to a known map
and game mode in the active HLL or HLL Vietnam catalogue; the parser's unknown
fallback is rejected.

Bulk results contain one status per player. Once a target fails or becomes
unknown, later targets are marked `not_attempted`. The receipt also stores the
service username, timestamps, revision scope and sanitized result as the audit
record. Message text and credentials are not copied into results.

## Release gate

1. Run Black, isort, contract tests, Django migration checks and the full
   repository suite locally without treating GitHub Actions as evidence.
2. Apply migration `0036_eventador_control_steps` to an isolated restored
   PostgreSQL database and run authentication, idempotency, stale-state,
   restart and both-game-profile tests.
3. Deploy with `EVENTADOR_CONTROL_ENABLED` absent and verify authenticated
   capability and state reads through the private WireGuard path.
4. Run the first mutation against isolated HLL and HLL Vietnam canaries with no
   production players or Discord output.
5. Enable production execution only for the exact owner-approved Eventador
   workflow revision, then record RCON and Eventador postflight evidence.

Disabling the flag blocks every new preparation and execute request immediately.
Existing `executing` receipts age into terminal `unknown`; they are never
converted back to `prepared`.
