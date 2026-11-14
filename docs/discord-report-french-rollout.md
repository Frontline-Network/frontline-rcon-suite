# French Discord report bot: candidate and deployment sequence

This document describes the local candidate. It does not assert that the shared Discord service or any customer installation has been updated.

## Scope and compatibility

- The RCON configuration and both copies of `ModerationPolicy` accept `de`, `en` and `fr`. Customer-supplied templates and player text are not translated or overwritten.
- The shared Discord service renders French report cards and selected asynchronous interaction responses. An authenticated incident event's language is persisted per installation and incident. Missing or invalid later language values preserve the stored language; stale revisions cannot replace it. A row lock serializes updates to an existing mapping on PostgreSQL.
- `discord_incident_message.discord_language` is added at service startup if absent. The default `de` preserves the historical German interaction behavior of existing mappings. Startup requires permission to alter that table; PostgreSQL takes a table lock for the additive DDL. Old service binaries ignore the extra column and its server-side default. Never drop the column as part of a routine rollback.
- The shared service serves multiple installations. Its deployment or restart affects every connected installation, not only AFL. Version compatibility, database rights, restart coordination and a tested restore point must be checked for the shared service before release.
- The candidate is not a claim that every external provider response, user-written text, old release, or technical backend error has a French translation. Unknown configured content stays verbatim. Where no incident can be identified, generic errors use the signed Discord client locale for French and retain the historical German fallback otherwise.

## Verification run on 14 November 2026

All service tests used the mounted local source with the container working directory set to the mount root. This matters: the existing test image contains an older copy under `/test` that otherwise takes precedence during imports.

```sh
docker run --rm --network none -w /mnt \
  -v /tmp/discord-french-isolated:/mnt:ro \
  -e PYTHONPATH=/mnt:/mnt/discord_service \
  --entrypoint python frontline/discord-service:v0.8.5-rc.1-948f4b48-tests \
  -m pytest -q -p no:cacheprovider /mnt/discord_service/tests --tb=short
```

Latest run after enabling the local policy and test-message changes: 155 passed, two PostgreSQL-only tests skipped. The two skipped tests were run separately against a disposable PostgreSQL 16 instance with no external network, using the same mounted source and `DISCORD_LANGUAGE_DEDICATED_TEST_DB=yes`:

```sh
docker run --rm --network container:codex-discord-fr-postgres -w /mnt \
  -v /tmp/discord-french-isolated:/mnt:ro \
  -e PYTHONPATH=/mnt:/mnt/discord_service \
  -e DISCORD_SERVICE_DATABASE_URL='postgresql+psycopg://TEST_USER:TEST_PASSWORD@127.0.0.1/TEST_DB' \
  -e DISCORD_SERVICE_SECRET='test-only-secret-at-least-32-characters' \
  -e DISCORD_SERVICE_DRY_RUN=true -e DISCORD_LANGUAGE_DEDICATED_TEST_DB=yes \
  --entrypoint python frontline/discord-service:v0.8.5-rc.1-948f4b48-tests \
  -m pytest -q -p no:cacheprovider \
  /mnt/discord_service/tests/test_incident_language_postgres.py --tb=short
```

Those two tests passed before the later policy/test-message changes. They cover migration of an old PostgreSQL table under four concurrent startup attempts, and concurrent revisions of an existing incident. The disposable PostgreSQL container was removed after testing. Repeat them on the final release build; the environment variable makes the test suite explicitly destructive to the designated database.

The RCON-side test was run against the isolated AFL test backend and its isolated test database:

```sh
docker exec -e PYTHONPATH=/code:/code/rconweb -e DJANGO_DEBUG=true \
  afl-ui-test-backend python /code/rconweb/manage.py test \
  api.tests.DiscordActionTemplateTests.test_french_discord_test_message_passes_selected_language \
  api.tests.DiscordActionTemplateTests.test_test_message_works_while_connected_in_paused_mode --verbosity 0
```

Both passed. Frontend checks for this area include `node --test src/i18n/fr-discord-reports.test.mjs`, `node --test src/pages/settings/report-admin/copy-fr.test.mjs` and the application-wide i18n/build checks.

## Safe rollout and rollback

1. Build and verify the complete shared service and AFL RCON candidates. Check the actual production database schema and service account's migration rights, ensure a tested backup/restore point, and arrange the shared-service restart for all affected installations. These steps are not performed by this document.
2. Deploy the backwards-compatible shared Discord service first. Verify startup, successful migration, health, and existing German/English delivery and interactions using isolated test fixtures or an explicitly authorized test channel. Keep all existing customer language settings unchanged. Old RCON instances continue sending `de`/`en`, which the new service accepts.
3. Only after the new shared service is confirmed healthy, deploy the RCON candidate to the intended instance. The new RCON exposes `fr` and can transmit it to the service; deploying this RCON first against an older service is unsafe because older policy schemas reject `fr` and older card renderers lack French dictionaries.
4. Set `fr` only for the intended installation if requested, then verify report creation, follow-up edits, role restrictions, moderation previews and confirmations in an authorized test channel. Preserve existing custom templates. Confirm live behaviour without issuing real player sanctions.
5. Before rolling the shared service back to a version that does not support `fr`, identify every installation and queued/retry event still carrying `fr`, coordinate a safe transition to `de` or `en`, and verify no incompatible pending deliveries remain. Otherwise old validators may reject events or old renderers may fail. Roll back the service image while leaving the additive language column in place; verify German/English delivery and service health. Do not silently rewrite stored customer preferences or discard queued incidents.

## Test message side effect

The RCON **test message** action is not a dry run. After authentication it calls the shared service, which calls `DiscordClient.upsert` and posts a real message in the configured Discord channel. This works even when the integration is paused. RCON also updates the persisted last-test timestamp, success flag and failure code. No live test was sent as part of this work; use a specifically authorized test channel or obtain the appropriate approval before sending.
