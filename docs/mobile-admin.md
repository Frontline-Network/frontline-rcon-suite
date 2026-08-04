# CRCON Mobile Admin

The integration is opt-in and disabled by default. It keeps CRCON as the only
source of users, roles, permissions, player data and administrative actions.
Each administrator pairs their own account; there are no shared QR codes.

## CRCON configuration

Set at least:

```env
MOBILE_INTEGRATION_ENABLED=true
MOBILE_PUBLIC_BASE_URL=https://crcon.example.org
MOBILE_INCIDENT_TRIGGERS=!admin
MOBILE_INCIDENT_RETENTION_DAYS=90
```

Run both Django and Alembic migrations during the normal maintenance startup.
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
