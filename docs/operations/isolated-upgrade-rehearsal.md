# Isolated backend upgrade rehearsal

`scripts/rehearse_upgrade.py` checks a real released backend image followed by a
candidate image. It applies the candidate twice and then boots the old web image
again. This last step is a **code rollback**, suitable only when the old code is
compatible with the candidate database schema. It does not reverse migrations.

The environment has its own PostgreSQL and Redis containers and anonymous data
volumes. PostgreSQL uses Docker's `none` network; all application processes and
Redis share that same isolated network namespace. No host ports are published.
The applications cannot send mail, Discord messages, push notifications, or RCON
commands to external services. No production containers or writable production
data directories are mounted. Startup cleanup and migrations affect only copies.

## Run against a released image

Use a Linux Docker host with sufficient temporary memory and disk space. Pull
the source release, candidate, PostgreSQL, and Redis images beforehand; the
rehearsal itself refuses to pull images. Prefer immutable digests. Use database
service versions compatible with the source installation; this is not a
PostgreSQL major-version upgrade procedure.

```bash
python3 scripts/rehearse_upgrade.py --state-dir /private/new-upgrade-test prepare \
  --source-image RELEASED_BACKEND_DIGEST \
  --postgres-image EXISTING_POSTGRES_IMAGE \
  --redis-image EXISTING_REDIS_IMAGE --game hllv

python3 scripts/rehearse_upgrade.py --state-dir /private/new-upgrade-test verify \
  --candidate-image CANDIDATE_BACKEND_DIGEST

python3 scripts/rehearse_upgrade.py --state-dir /private/new-upgrade-test cleanup
```

`prepare` refuses any existing state directory. Without backup arguments it
starts from empty databases and creates a synthetic staff account, group and
log-reading permission, API key, and individual display preferences. It does not
grant this account sanction permissions or superuser access.

To test a customer snapshot, add the following arguments to `prepare`:

```bash
  --backup /private/paired-backup/postgres.dump --backup-sha256 EXPECTED_SHA256 \
  --redis-backup /private/paired-backup/redis.rdb --redis-backup-sha256 EXPECTED_SHA256
```

Use PostgreSQL custom-format dumps and Redis RDB snapshots from the same backup
operation. Both files are verified before restore and mounted read-only.
Credentials and command logs remain in the private state directory. They must
not be published as CI artifacts. `cleanup` removes only recorded containers
whose full IDs, ownership labels and network isolation still match. It removes
their disposable volumes but retains the backup files and the test receipt.

## What is checked

- Actual maintenance and web entrypoints, HTTP readiness and WebSocket listener.
- Password login, session authentication, API-key authentication, invalid-key
  rejection, missing-CSRF rejection, denied kick permissions, admin index and
  live-log read access over HTTP.
- Unauthorized Barricade WebSocket handshake rejection.
- Identical content hashes for customer accounts, passwords, groups, rights,
  API keys, UI preferences, stored Discord integration and server configuration,
  plus Django/Alembic migration history. The synthetic user row is excluded
  because test logins necessarily update its `last_login`; all customer user
  rows remain included. Authentication and denied permissions of the fixture
  are checked through HTTP.
- Unchanged row counts for the listed gameplay, VIP, log, statistics, and report
  tables. Audit entries belonging only to the unique synthetic test account are
  excluded because denied permission probes create new audit events. They are
  retained in the test database. These counts do not prove byte-for-byte
  equality of the large tables.
- Repeatability of the update and continued operation after code rollback.

The source and candidate share a fresh synthetic application secret. Stored
customer secrets are compared unchanged but their decryption and external
integration behavior are not exercised. The probe deliberately never tests an
actual kick, outbound notification, game round transition, or browser rendering.
Those require separate functional acceptance before publishing a release.

This initial preservation check expects unchanged migration history, matching
the schema-preserving changes after v0.9.3. A future release that changes the
schema needs reviewed migration-specific expectations and its own rollback
strategy; do not disable the comparisons just to make such a release pass.

`verified.json` records image IDs, preservation evidence, observed request
durations, and stage results. Single request timings are diagnostic observations,
not a load benchmark. The manual GitHub workflow `upgrade-rehearsal.yml` runs the
synthetic path for both HLL and HLLV, with both `split` and `unified` API modes,
and uploads only this receipt. Select the same mode locally with `--api-mode`.

## Check backend packaging separately

```bash
docker run --rm --network none --entrypoint python CANDIDATE_BACKEND_DIGEST \
  scripts/check_backend_image.py --slim
docker run --rm --network none --entrypoint python CANDIDATE_BACKEND_DIGEST \
  -m pip check
```

This verifies runtime executables, native Python imports, migrations, Django
templates/static files, release metadata and release-verification scripts. It
also rejects build-only files in the slim image. The separate frontend build
continues to receive its original full frontend context.
