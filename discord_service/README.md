# Frontline CRCON Discord Service

Central Discord delivery and customer-funded moderation analysis for CRCON. The
service is deliberately a separate deployment: customers install the Frontline
Discord app without managing a bot token, then connect either their own OpenAI
API key or their ChatGPT/Codex account for optional AI checks.

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

Player names use the separate `DISCORD_SERVICE_PLAYER_NAME_MODEL` (default:
`gpt-5.4-nano`) with a compact schema and low reasoning; they do not call the
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
- `DISCORD_SERVICE_OPENAI_API_KEY`: used only for the Omni moderation gate in
  ChatGPT/Codex mode; it is never used for generative analysis or customer quota.
- `DISCORD_SERVICE_DISCORD_INSTALL_URL`: OAuth installation URL for that app.
- `DISCORD_SERVICE_ALLOWED_CRCON_HOSTS`: optional comma-separated exact host
  allowlist. Pairing always rejects private/link-local callback targets and any
  path other than CRCON's pairing callback.

Do not place capabilities in URLs or logs. Pairing is valid for ten minutes and
creates separate random capabilities for CRCON-to-service events and
service-to-CRCON actions. The receiver stores only a keyed digest; the sender
stores the raw value encrypted.

## AI providers

CRCON offers two provider modes per installation:

- **Own API key** keeps the key encrypted in CRCON and sends it only with the
  individual analysis request over the existing authenticated HTTPS channel.
  The central service does not persist it.
- **ChatGPT/Codex** starts the official Codex device-code flow. OAuth state is
  encrypted per installation on the `discord_codex` volume and is only
  materialized in a temporary `CODEX_HOME` while the Codex process needs it.
  Before untrusted text reaches a model turn, the plaintext credentials are
  detached again. The model list is read dynamically from that signed-in
  account. CRCON never receives or displays the OAuth tokens.

The Codex mode is deliberately isolated and read-only: every moderation turn is
ephemeral, uses a strict JSON schema, has no writable workspace or built-in
execution/search tools, and runs with approval policy `never`. If authentication,
plan quota, the selected model, or the runtime is unavailable, moderation is
marked unavailable while ordinary Discord reports continue to work.

The central service has no Frontline-funded AI fallback. Legacy installations
that still contain `provider: managed` are migrated to disabled AI sources until
the customer explicitly configures one of the two supported providers.

## Verification

```bash
python -m pytest
```

Set `DISCORD_SERVICE_DRY_RUN=true` only for isolated development or tests. In
that mode Discord writes are simulated and non-HTTPS callback URLs are allowed.

## Mobile player report panel

Set `FRONTLINE_VOICE_REPORT_SERVERS` to the comma-separated server numbers that
should accept voice reports. Apply it to the backend, game routines and Discord
worker. Leave `FRONTLINE_VOICE_LIVE_KICK_SERVERS` empty during acceptance:
players receive the private notice and follow-up while the final kick is
simulated. A live kick requires both server flags, active report moderation,
and a timely explicit reply from the eligible witness for that case.

After enabling the voice-report pilot on the selected RCON server, publish its
player panel from the Discord service container. Use the installation's paired
guild ID and the player-facing text channel chosen by the community.

```sh
python -m app.publish_player_panel --installation <installation-id> --server <server-number> --guild <guild-id> --channel <player-channel-id>
```

Running the command again updates the same Discord message. Each panel routes
new reports, language choices and private case replies to its bound RCON
server. Players can link their game account or change DM delivery through
**My reports**. Case updates edit the author's private interaction for up to
14 minutes. Later updates remain available through **My reports**, with
additional DMs for players who enabled them.

If profiles on one installation run different RCON versions, the panel can use
a dedicated player callback. Add `--callback-origin https://<profile-host>` to
the publish command. The host must appear in the Discord service’s existing
`ALLOWED_CRCON_HOSTS` setting (environment prefix `DISCORD_SERVICE_`). The
publisher verifies the installation and probes the selected profile before it
posts or updates the panel. Other callbacks keep the paired installation URL.
Use `--use-installation-callback` to restore that URL for this panel.
