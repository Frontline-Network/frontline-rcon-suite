# Performance and scaling

This document records measured runtime costs and the safeguards used when
optimizing Frontline RCON Suite for multi-instance hosts. Measurements must be
repeated on the same host and workload before and after a rollout.

## August 2026 baseline

The four-gameserver production installation used for the initial baseline had
8 CPU cores and 31 GiB RAM. It was serving real HLL/HLL Vietnam traffic.

| Component | Measured baseline |
| --- | ---: |
| One supervisor container | 1.17-1.44 GiB RAM |
| One backend container | 397-903 MiB RAM |
| One Django mobile/Discord worker | about 171 MiB RAM |
| Redis | about 500 MiB RAM |
| PostgreSQL database | about 16 GiB on disk |
| `log_lines` table and indexes | about 12 GiB on disk |
| Idle PostgreSQL client connections | 63 |
| Redis `SCAN` rate | about 16.8 calls/second |
| Mobile push worker with three devices | 16-20% of one CPU core |

The supervisor footprint is primarily multiple independent Python
interpreters. The initial low-risk phase therefore targets avoidable wakeups,
database transactions, Redis discovery and repeated API work. Process
consolidation is a separate phase because it changes failure isolation.

## Runtime changes in the first phase

- The live statistics loop sleeps until the next configured refresh deadline
  instead of waking ten times per second.
- Long-lived supervisor commands retain one SQLAlchemy connection and use at
  most two temporary overflow connections by default. Explicit `NullPool`
  configuration still takes precedence.
- Mobile push polling backs off while idle, caches device and permission
  discovery, reuses HTTP connections, and never keeps its SQL transaction open
  while contacting the relay.
- Webhook producers maintain a small Redis queue registry. The consumer scans
  legacy keys once during upgrade, then reads the registry. An initialized
  sentinel prevents empty installations from repeatedly scanning Redis.
- The webhook loop uses a longer idle sleep while retaining the original short
  active delay.
- Completed historical scoreboards are cached across API workers. Current
  matches bypass this cache. Public UI queries treat completed matches as
  immutable.
- Scalar server-setting changes delete their exact Redis cache key rather than
  scanning the complete logical database. Full cache invalidations request 500
  keys per scan step to reduce command amplification.

## RCON1-4 canary result

The phase-one images were rolled out server by server on the four-instance
host. Both HLL and HLL Vietnam profiles remained reachable throughout the
canary.

| Check | Canary result |
| --- | ---: |
| Public RCON response | HTTP 200, 32-44 ms during verification |
| Mobile push idle CPU | 0.00% in repeated samples |
| Webhook idle CPU | 0.19-0.24% |
| Redis SCAN before exact invalidation | 1,671 calls in 30 seconds |
| Redis SCAN after exact invalidation | 2 calls in 40 seconds |
| PostgreSQL mobile transaction | idle connection, no `idle in transaction` |
| Backend RAM after warmup | 316-571 MiB per instance |
| Supervisor RAM after warmup | 1.11-1.41 GiB per instance |

The measured Redis reduction is greater than 99.9% for the sampled windows.
Supervisor RAM remains the largest scalable cost and is addressed separately.

## Process consolidation phase

RQ's worker-side scheduler remains responsible for delayed queue jobs such as
temporary broadcasts. The separate `rqscheduler` process existed only for the
periodic performance-statistics dump. That dump now runs on its own monotonic
deadline inside the existing routines service, preserving its configured
interval while removing one Python process per gameserver.

Gunicorn preload is also skipped by default when only one worker is configured.
This retained the split HTTP/WebSocket architecture while reducing backend RAM
materially on busy instances.

Long-lived Gunicorn workers recycle after a bounded number of requests. The
master starts a replacement before retiring the old worker, while jitter keeps
multiple CRCON instances from recycling simultaneously. This bounds RSS after
large history/scoreboard responses whose temporary Python allocations are not
returned to the operating system.

A single Daphne process serving ports 8000 and 8001 was measured as an explicit
low-memory mode. It reduced the HLLV backend from about 304 MiB to 147-165 MiB,
but a ten-client unauthorized API benchmark dropped from about 180 to 96
requests/second. A 200-OK documentation benchmark also favored split mode
(18.25 versus 16.34 requests/second). `unified` therefore remains opt-in and
must not be the production default.

The Mobile Push, Discord event and Discord moderation loops can be run in one
shared process with `compose.combined-workers.yaml`. The loops remain isolated
in three threads with their own HTTP and database sessions, so a 180-second AI
request cannot block a report or push notification. The Discord outbox commits
its SQL transaction before every broker or AI request. Background-only Django
commands also skip URL/view system checks.

On the RCON1-4 canary, the three split workers consumed about 165 MiB each
(about 495 MiB total). The combined process consumed 164.3 MiB with all three
threads running, saving about 331 MiB (67%) for this worker group. Its five
database clients were all `idle`; none was `idle in transaction`. All four
public RCON endpoints returned HTTP 200 in 33-37 ms during the switch.

Enable the opt-in mode with:

```bash
docker compose --profile combined-workers \
  -f compose.yaml \
  -f compose.mobile-admin.yaml \
  -f compose.combined-workers.yaml up -d --remove-orphans
```

Do not run this profile concurrently with the split workers. Event and broker
idempotency are still retained as a last-resort retry safeguard.

## Configuration

All settings are optional and existing installations receive conservative
defaults.

| Variable | Default | Purpose |
| --- | ---: | --- |
| `HLL_DB_POOL_SIZE` | `1` | Persistent SQLAlchemy connections per supervisor process |
| `HLL_DB_MAX_OVERFLOW` | `2` | Temporary connections allowed during a short burst |
| `HLL_DB_POOL_RECYCLE` | `900` | Seconds before a retained connection is recycled |
| `HLL_API_SERVER_MODE` | `split` | `unified` is an opt-in low-memory ASGI mode; split Gunicorn + Daphne retains higher concurrency |
| `HLL_GUNICORN_PRELOAD` | `auto` | Preload for multiple API workers; disabled automatically for one worker |
| `HLL_GUNICORN_MAX_REQUESTS` | `1000` | Recycle a split Gunicorn worker after this many requests; zero disables recycling |
| `HLL_GUNICORN_MAX_REQUESTS_JITTER` | `100` | Random extra requests before recycling to stagger instances |
| `HLL_WH_IDLE_SLEEP_TIME` | `0.1` | Webhook loop delay when no queue has work |
| `HLL_HISTORICAL_SCOREBOARD_CACHE_SECONDS` | `21600` | Completed scoreboard cache lifetime |
| `MOBILE_PUSH_ACTIVE_POLL_SECONDS` | `1` | Push polling delay after successful work |
| `MOBILE_PUSH_IDLE_POLL_SECONDS` | `10` | Maximum push polling delay while idle |
| `MOBILE_PUSH_DEVICE_CACHE_SECONDS` | `60` | Device and permission cache lifetime |
| `DISCORD_WORKER_ACTIVE_POLL_SECONDS` | `0.25` | Delay after successful Discord outbox work |
| `DISCORD_WORKER_IDLE_POLL_SECONDS` | `1` for event/mixed workers, `10` for moderation-only | Maximum idle polling delay |

## Database lifecycle phase

The RCON1-4 database contained an estimated 1.05 million `log_lines` rows but
used 12 GiB: 6.1 GiB heap and 6.7 GiB indexes. The 4.8-GiB
`unique_log_line` index had 943,425 recorded scans, so it must not simply be
dropped. Replacing its large raw-text key with a compact fingerprint requires
a dedicated compatibility migration and is not part of the low-risk phase.

`audit_log` contained 2.54 million rows and used 1.45 GiB. It had no index on
`creation_time`; requesting the newest 50 rows therefore planned a parallel
full-table scan and sort (estimated plan cost about 200,401). Migration
`b8e3a1f4c6d2` creates `ix_audit_log_creation_time` concurrently so reads and
writes are not blocked while the index is built. Schedule this migration for a
low-I/O maintenance window and verify free disk space first.

The `runtime_data_retention` command is disabled unless a retention period is
configured and is always a dry-run unless `--execute` is supplied. It samples
only the maximum bounded work set and deletes in separately committed batches:

```bash
python rconweb/manage.py runtime_data_retention \
  --log-days 180 --audit-days 365 --batch-size 1000 --max-batches 10

# Only after reviewing the dry-run and taking a backup:
python rconweb/manage.py runtime_data_retention \
  --log-days 180 --audit-days 365 --batch-size 1000 --max-batches 10 --execute
```

| Variable | Default | Purpose |
| --- | ---: | --- |
| `HLL_LOG_RETENTION_DAYS` | `0` | Raw game-log retention; zero disables it |
| `HLL_AUDIT_RETENTION_DAYS` | `0` | CRCON audit retention; zero disables it |
| `HLL_RETENTION_BATCH_SIZE` | `1000` | Rows committed per delete transaction, capped at 10,000 |
| `HLL_RETENTION_MAX_BATCHES` | `10` | Maximum batches per invocation, capped at 1,000 |

Normal batched deletes make space reusable inside PostgreSQL but do not shrink
the data files. Disk reclamation (`VACUUM FULL`, `REINDEX`, or `pg_repack`) is a
separate maintenance operation with its own capacity and rollback plan.

## Canary measurement

Capture at least five minutes before and after a restart, excluding image
build time and the first cache warmup.

1. Record container CPU and memory with repeated `docker stats --no-stream`.
2. Record Redis `INFO commandstats` twice, 60 seconds apart. In normal idle
   operation, `SCAN` should remain at zero after the one-time registry import.
3. Record PostgreSQL connections grouped by `application_name` and state.
   There must be no mobile push connection left `idle in transaction`.
4. Request the same completed map scoreboard at least three times. The first
   request may build the cache; later requests should avoid the historical log
   query and have materially lower latency.
5. Verify live logs, webhook delivery, mobile notification, Discord report
   delivery and one HLLV scoreboard before expanding the rollout.

## Rollback

The phase has no schema migration and does not delete data. Roll back by
deploying the previous image. The Redis queue registry is additive and harmless
to older releases. To restore previous timing temporarily, set
`HLL_WH_IDLE_SLEEP_TIME=0.006` and `MOBILE_PUSH_IDLE_POLL_SECONDS=1`.

To roll back combined delivery workers, stop `frontline_background_worker` and
start `mobile_push_worker`, `discord_report_worker` and
`discord_moderation_worker` with the normal Mobile Admin Compose stack. Never
leave both modes running together.

Database retention and index replacement require their own migration, backup
and rollback plans. Process consolidation must be canaried separately from
database lifecycle work.
