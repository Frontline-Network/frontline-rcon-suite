# Frontline CRCON Discord Service

Central Discord delivery and managed moderation analysis for CRCON. The service is
deliberately a separate deployment: customers install the Frontline Discord app
and do not manage a bot token or OpenAI key themselves.

## Local start

1. Copy `.env.example` to `.env` and replace every secret.
2. Set `DISCORD_POSTGRES_PASSWORD` in the shell or a Compose environment file.
3. Run `docker compose up -d --build`.
4. Terminate TLS in the reverse proxy and expose only HTTPS publicly.
5. Set the Discord Interactions Endpoint URL to
   `https://<service>/v1/discord/interactions`.

The service stores integration bindings, capability material, incident/message
mappings, short-lived encrypted confirmation relays, idempotency receipts, and
content-free usage metrics. It has no database column for report/chat/name text,
action reasons, messages, or previews.

`DISCORD_SERVICE_MONTHLY_TOKEN_QUOTA=0` means no fixed service-side quota. A
positive value is enforced per CRCON installation and is displayed in CRCON.

Player names use the separate `DISCORD_SERVICE_PLAYER_NAME_MODEL` (default:
`gpt-5-nano`) with a compact schema and low reasoning; they do not call the
generic moderation endpoint first. Chat candidates use `DISCORD_SERVICE_AI_MODEL`
only after the moderation/policy gate. Normal player reports are delivered
without AI analysis. CRCON stores the last normalized
name per player identity, model, and policy version locally, so an unchanged
name is not sent for another AI check.

## Required security settings

- `DISCORD_SERVICE_SECRET`: random value with at least 32 characters; changing it
  invalidates encrypted action capabilities and pending confirmations.
- `DISCORD_SERVICE_DISCORD_PUBLIC_KEY`: verifies every Discord interaction.
- `DISCORD_SERVICE_DISCORD_BOT_TOKEN`: the one Frontline-managed bot token.
- `DISCORD_SERVICE_OPENAI_API_KEY`: the Frontline-managed OpenAI project key.
- `DISCORD_SERVICE_DISCORD_INSTALL_URL`: OAuth installation URL for that app.
- `DISCORD_SERVICE_ALLOWED_CRCON_HOSTS`: optional comma-separated exact host
  allowlist. Pairing always rejects private/link-local callback targets and any
  path other than CRCON's pairing callback.

Do not place capabilities in URLs or logs. Pairing is valid for ten minutes and
creates separate random capabilities for CRCON-to-service events and
service-to-CRCON actions. The receiver stores only a keyed digest; the sender
stores the raw value encrypted.

## Verification

```bash
python -m pytest
```

Set `DISCORD_SERVICE_DRY_RUN=true` only for isolated development or tests. In
that mode Discord writes are simulated and non-HTTPS callback URLs are allowed.
