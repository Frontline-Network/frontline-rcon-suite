# Frontline VIP lifecycle campaigns

The lifecycle campaign is a private Frontline Network extension and a personal
`MessagePlayer` workflow. It is disabled and hidden unless the installation-wide
feature flag is explicitly enabled. Regular CRCON installations continue to see
and use only the normal campaign function.

## WordPress status contract

CRCON sends one `POST` request for all currently connected, non-blocked players:

```json
{
  "player_ids": ["76561198000000001", "player-2"],
  "server_family": "hll_vietnam"
}
```

Endpoint:

```text
https://fln.gg/wp-json/frontline-vip/v1/lifecycle-status
```

The request uses the same `FRONTLINE_VIP_REDEEM_SECRET` as account verification.
The exact JSON bytes are authenticated with these headers:

- `X-FLN-Timestamp`: Unix timestamp, accepted within five minutes
- `X-FLN-Nonce`: 32 lowercase hexadecimal characters, accepted once
- `X-FLN-Signature`: HMAC-SHA256 over `timestamp + "\n" + nonce + "\n" + body`

The response contains no account, email, billing, or order details:

```json
{
  "success": true,
  "server_family": "hll_vietnam",
  "generated_at": "2026-09-03T12:00:00+00:00",
  "players": [
    {
      "player_id": "76561198000000001",
      "server_family": "hll_vietnam",
      "status_known": true,
      "verified": true,
      "vip_active": true,
      "grant_source": "trial",
      "expires_at": "2026-09-05T12:00:00Z",
      "has_purchased_vip": false,
      "status_version": "sha256-status-fingerprint"
    }
  ]
}
```

Invalid signatures, stale timestamps, replayed nonces, invalid player IDs, more
than 100 players, and unknown server families are rejected. CRCON validates each
response row again and skips missing or ambiguous rows.

## Runtime configuration

```dotenv
FRONTLINE_VIP_REDEEM_URL=https://fln.gg/wp-json/frontline-vip/v1/redeem
FRONTLINE_VIP_STATUS_URL=https://fln.gg/wp-json/frontline-vip/v1/lifecycle-status
FRONTLINE_VIP_REDEEM_SECRET=the-same-secret-as-wordpress
FRONTLINE_VIP_LIFECYCLE_ENABLED=true
```

`FRONTLINE_VIP_STATUS_URL` is optional when the redeem URL ends in `/redeem`;
CRCON derives the lifecycle endpoint automatically.

`FRONTLINE_VIP_LIFECYCLE_ENABLED` defaults to `false`. When disabled, the panel
is not rendered, automatic processing is skipped, manual preview/test operations
are rejected, and a copied database configuration cannot reactivate the private
feature. Normal broadcast and direct-message campaigns remain unchanged.

## Delivery guarantees

- Unverified players get one invitation from their second visit onwards. A
  visit spans reconnects and server changes until a confirmed break of at least
  30 minutes. Prior sessions are matched to their recorded CONNECTED event
  and game family. Ambiguous history does not establish a return visit.
- The active trial notice is sent once. Expiring and expired share one notice:
  expiry is a fallback for players who missed the reminder. The reminder
  window defaults to 48 hours. Paid or blocked players are excluded.
- Claims are scoped to the player and game family in the shared installation
  database. WordPress offers one free trial per account and family. A provider
  supporting multiple trials may supply a stable string `trial_id` per grant.
  Edits to expiry or status version never trigger another reminder. Without
  an identifiable grant, the one-time trial is treated conservatively.
- Test mode persists simulations but never sends an automatic message.
- Manual test messages are explicit, logged separately, and do not consume a
  regular lifecycle delivery.

Lifecycle status timestamps use UTC. Session start times use the absolute event
timestamp when available; older sessions can still contain a naive local start,
so their minimum-session-time calculation depends on the historical server time
zone. Status responses are cached for 60 seconds by default and all connected
players are queried in one request.

## Database migration

Alembic revision `9f3c2d1a6b40` creates `vip_lifecycle_deliveries`. Existing automatic attempts, including ambiguous sends, count
toward the family limit. Historical rows without a grant identifier suppress a
possible duplicate for the corresponding stage. Manual tests and simulations
are kept separate from live claims. The player row is locked during reservation
so workers on different servers cannot both claim the same notification.
The shared message interval and per-player gap also limit timing.

Do not enable the feature until the WordPress plugin and database migration are
installed and the signed status endpoint has passed a read-only smoke test.

## Safe deployment sequence (later, after explicit approval)

1. Leave `vip_lifecycle.enabled=false` on every instance.
2. Create full backups of the WordPress database and plugin files, plus every
   affected CRCON PostgreSQL database, Redis data set, environment file, and
   deployed application/configuration volume.
3. Verify the backups with checksums and a restore test into isolated temporary
   WordPress and CRCON environments. A successful backup command alone is not a
   verified backup.
4. Install the reviewed Frontline VIP plugin build first. Confirm the existing
   checkout, verification, order completion, expiry display, and RCON sync flows.
5. Configure the same 32-or-more-character secret on WordPress and CRCON. Set
   `FRONTLINE_VIP_STATUS_URL`, or verify that it is derived correctly from the
   `/redeem` URL. Never print the secret in deployment logs.
6. Send a signed, read-only lifecycle status request for controlled test IDs.
   Verify authentication rejection, server-family isolation, UTC timestamps,
   paid-VIP exclusion, and that no account/order fields are returned.
7. Apply the application's migrations, including `9f3c2d1a6b40`, to each CRCON
   database and verify the expected head for the deployed version before restart.
8. In one non-production or canary instance, keep the lifecycle function in test
   mode, inspect the audience preview and delivery log, and send one explicit
   manual test message to a consenting test player.
9. Enable automatic delivery on one canary server family. Observe WordPress and
   CRCON logs for one full map cycle before expanding instance by instance.
10. To stop delivery, disable the lifecycle switch immediately. The migration is
    additive and should normally remain in place during an application rollback;
    restore databases/files only from the verified backups when necessary.
