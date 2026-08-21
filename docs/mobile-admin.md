# CRCON Mobile Admin

The integration is opt-in and disabled by default. It keeps CRCON as the only
source of users, roles, permissions, player data and administrative actions.
Each administrator pairs their own account; there are no shared QR codes.

## CRCON configuration

Set at least:

```env
MOBILE_INTEGRATION_ENABLED=true
MOBILE_PUBLIC_BASE_URL=https://crcon.example.org
CORS_ALLOWED_ORIGINS=https://webapp.example.org
MOBILE_INCIDENT_TRIGGERS=!admin
MOBILE_INCIDENT_RETENTION_DAYS=90
MOBILE_CONTEXT_V2=shadow
MOBILE_CONTEXT_FUZZY_THRESHOLD=0.74
```

`CORS_ALLOWED_ORIGINS` accepts comma-separated, complete origins. Add only the
trusted browser frontends that need to call this CRCON installation; do not use
a wildcard for authenticated mobile API requests.

## Deployment security

`RCONWEB_API_SECRET` is mandatory outside the explicit test setting
`RCONWEB_TEST_MODE=true`. Use a unique, randomly generated value with at least
32 characters for every installation. Short legacy values remain temporarily
compatible so an update does not cause an outage, but CRCON logs a warning and
they should be rotated during planned maintenance.

Credentialed browser origins must be explicit HTTPS origins in production. Do
not derive them from hostnames and do not include paths, query strings or HTTP
origins. For example:

```env
RCONWEB_API_SECRET=<unique-random-secret-with-at-least-32-characters>
CORS_ALLOWED_ORIGINS=https://webapp.example.org,https://ops.example.org
```

Run both Django and Alembic migrations during the normal maintenance startup.
For Frontline production hosts, follow the guarded GitHub deployment workflow in
[`production-deploy.md`](production-deploy.md); it preserves the migration graph
already used by production and creates a database backup before every rollout.
The **Settings → CRCON App → Mobile Admin App** card then creates a two-minute,
one-time QR code. The administrator must compare the six-digit code shown on
both devices and approve the phone in the authenticated CRCON browser.

Production pairing rejects HTTP. A debug Flutter build and Django `DEBUG` mode
may use HTTP for local development only.

## Incidents

With the integration enabled, chat messages such as
`!admin Player Name reason` create incidents. Multiple trigger words can be
comma-separated in `MOBILE_INCIDENT_TRIGGERS`. Exact unique online names are
linked automatically; ambiguous names remain unlinked. Identical reports from
the same player and server are deduplicated for 60 seconds.

If `MOBILE_INCIDENT_TRIGGERS` is left empty, CRCON inherits the existing Admin
Ping trigger words and falls back to `!admin` when none are configured.

### Player and squad context v2

`MOBILE_CONTEXT_V2` controls the richer resolver independently from pairing:

- `disabled` keeps the original single-player prefix resolver.
- `shadow` stores detected player and squad candidates as suggestions only.
- `enabled` automatically confirms only unique exact matches. Fuzzy matches
  remain suggestions and can never be used as an action target until an admin
  confirms them.

Incidents retain immutable reporter and subject snapshots while the app shows
the current server state alongside them. A single incident can contain several
player and squad subjects. Squad members must always be selected individually;
there are no squad-wide actions and a squad leader is never selected
implicitly. Existing `target_id` and `target_name` clients continue to receive
the primary confirmed player, or the confirmed squad leader for compatibility.

The mobile API adds permission-aware player search and dossiers, live rosters,
squad details, and revision/idempotency-protected subject mutations under
`/api/mobile/v1`. Missing CRCON permissions omit or lock the affected dossier
sections rather than broadening access.

Schedule retention cleanup once per day:

```bash
python rconweb/manage.py mobile_incident_cleanup
```

## Push

Deploy `push_relay/`, configure `MOBILE_PUSH_RELAY_URL`, and start the optional
Compose profile:

```bash
docker compose --profile mobile up -d mobile_push_worker
```

The worker checks active CRCON permissions for every delivery. Relay payloads
contain only installation UUID, incident UUID, event type and timestamp. They
never contain player names, player IDs, report reasons or admin notes.

Build the Flutter client with the matching relay URL:

```bash
flutter build appbundle --dart-define=PUSH_RELAY_URL=https://push.example.org
```

Firebase configuration files are intentionally not committed. Self-hosted iOS
and Android push builds must supply their own Firebase project and APNs setup.

The relay limits unauthenticated device registration to 120 requests per
client and minute and 10,000 stored devices by default. Adjust
`RELAY_REGISTRATION_RATE_LIMIT_PER_MINUTE` and
`RELAY_MAX_REGISTERED_DEVICES` to the expected installation size. Existing
push tokens register idempotently, so retrying does not invalidate capabilities
already stored by temporarily offline CRCON installations.

## Security lifecycle

- Access tokens are opaque, hashed in CRCON and expire after 15 minutes.
- Refresh tokens rotate on every use, expire after 30 idle days and have a
  180-day absolute lifetime.
- Device revocation, user deactivation and permission changes take effect on
  the next request.
- Mobile secrets live only in Keychain/Android secure storage; the encrypted
  Drift cache uses a separate 256-bit key from the same OS keystore.
- Kick and temporary ban require a reason and explicit confirmation. Mobile
  writes are never queued or retried offline.

## Beta end-to-end verification

The repository includes a gated runner at
`scripts/mobile_admin_beta_e2e.py`. It operates on an incident that was
created by an in-game report and is safe by default: it bootstraps the
connection, reads the incident, claims it, optionally adds a note, and
resolves it. It never executes a player action unless the operator supplies
`--allow-action` plus an explicit confirmed player and subject.

After sending a unique test report in-game, run the safe workflow with a
dedicated mobile access token:

```bash
export CRCON_BASE_URL=https://crcon.example.org
export CRCON_ACCESS_TOKEN='opaque-access-token'
export CRCON_TEST_INCIDENT_ID='incident-uuid-from-the-inbox'
python scripts/mobile_admin_beta_e2e.py --note 'Beta E2E: context and workflow verified'
```

For an authorized action test, use a dedicated test player and copy the
confirmed player subject id from the incident response. The explicit gate is
required for every action, including a temporary ban:

```bash
python scripts/mobile_admin_beta_e2e.py \
  --allow-action --action temp_ban \
  --player-id 7656119... --subject-id subject-uuid \
  --reason 'CRCON mobile beta test' --duration-hours 1
```

The runner creates a fresh idempotency key for each write, checks that the
player belongs to a confirmed subject, and aborts before any action when the
gate or context is incomplete. Do not use a production player or a shared
administrator token for this check.
