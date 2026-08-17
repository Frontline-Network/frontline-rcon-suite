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

## Configuration

All settings are optional and existing installations receive conservative
defaults.

| Variable | Default | Purpose |
| --- | ---: | --- |
| `HLL_DB_POOL_SIZE` | `1` | Persistent SQLAlchemy connections per supervisor process |
| `HLL_DB_MAX_OVERFLOW` | `2` | Temporary connections allowed during a short burst |
| `HLL_DB_POOL_RECYCLE` | `900` | Seconds before a retained connection is recycled |
| `HLL_WH_IDLE_SLEEP_TIME` | `0.1` | Webhook loop delay when no queue has work |
| `HLL_HISTORICAL_SCOREBOARD_CACHE_SECONDS` | `21600` | Completed scoreboard cache lifetime |
| `MOBILE_PUSH_ACTIVE_POLL_SECONDS` | `1` | Push polling delay after successful work |
| `MOBILE_PUSH_IDLE_POLL_SECONDS` | `10` | Maximum push polling delay while idle |
| `MOBILE_PUSH_DEVICE_CACHE_SECONDS` | `60` | Device and permission cache lifetime |

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

Database retention, index replacement and worker consolidation require their
own migration, backup and rollback plans. They must not be combined with this
canary phase.
