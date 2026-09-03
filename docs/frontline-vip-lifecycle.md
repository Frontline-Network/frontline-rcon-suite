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

- Unverified: at most once per configured cooldown, seven days by default.
- Active free VIP: once for the current free period.
- Expiring free VIP: once inside the configured window, 48 hours by default.
- Expired free VIP without a paid purchase: once after expiry.
- Paid VIP, blocked players, family mismatches, invalid timestamps, missing rows,
  and API failures: no message.
- Test mode persists simulations but never sends an automatic message.
- Manual test messages are explicit, logged separately, and do not consume a
  regular lifecycle delivery.

All comparisons use timezone-aware UTC timestamps. Status responses are cached
for 60 seconds by default and all connected players are queried in one request.

## Database migration

Alembic revision `9f3c2d1a6b40` creates `vip_lifecycle_deliveries`. The unique
status fingerprint prevents reconnects, map changes, and worker restarts from
repeating a one-time lifecycle message.

The delivery claim is committed before the RCON call. A failed or interrupted
attempt is logged but is not retried automatically for the same status
fingerprint, because an RCON timeout cannot prove that the player did not see
the message. This deliberately favours no duplicate advertising. A materially
changed WordPress status produces a new fingerprint and may become eligible.

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
7. Apply Alembic revision `9f3c2d1a6b40` to each CRCON database, verify that it
   is the sole migration head, then deploy/restart the CRCON application.
8. In one non-production or canary instance, keep the lifecycle function in test
   mode, inspect the audience preview and delivery log, and send one explicit
   manual test message to a consenting test player.
9. Enable automatic delivery on one canary server family. Observe WordPress and
   CRCON logs for one full map cycle before expanding instance by instance.
10. To stop delivery, disable the lifecycle switch immediately. The migration is
    additive and should normally remain in place during an application rollback;
    restore databases/files only from the verified backups when necessary.
