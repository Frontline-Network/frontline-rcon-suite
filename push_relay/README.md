# CRCON Push Relay

The relay deliberately cannot read CRCON reports. It stores only the FCM token,
random device handle, platform, and a hashed notify capability. Notification
payloads accept exactly four opaque fields: connection key, incident UUID,
event type, and timestamp.

Run locally with `RELAY_SECRET` set and `RELAY_DRY_RUN=true`:

```bash
uvicorn app.main:app --reload --port 8080 --no-access-log
```

For production, provide a Firebase service account through
`GOOGLE_APPLICATION_CREDENTIALS`, persistent PostgreSQL or SQLite storage, and
TLS termination. An iOS self-hosted build must use the operator's Firebase/APNs
configuration.

Keep HTTP access logging disabled: notify routes contain the opaque device
handle. Neither CRCON nor the relay application logs capabilities, push tokens,
device handles or notification bodies.
