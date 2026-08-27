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

## API and proxy hardening

Backend health now probes a dependency-free Django `/healthz` response and the
local WebSocket listener. A PID alone was insufficient because Gunicorn can
exist while Django is still importing and cannot serve requests. Compose only
marks the backend healthy after both ports are ready.

The frontend resolves its Compose `backend` alias through Docker DNS with a
short cache lifetime. This prevents a recreated backend container from leaving
Nginx pinned to its old address. The RCON3 canary moved the backend from
`192.168.48.2` to `192.168.48.5`; the public API returned HTTP 200 without
restarting the frontend, then recovered again after the normal address was
restored.

An external API client was observed requesting `get_recent_logs` without a
range every 30 seconds. The previous public API default returned 10,000 log
records and produced an 8.6-MiB JSON response. The public default is now 500,
matching the established example payload, while explicit ranges and internal
time-based automod scans remain unchanged. The same production response fell
to 380 KiB, a 95.6% reduction.

Each frontend serves one CRCON instance, so Nginx now uses one event-driven
worker instead of one worker per host CPU. On the eight-core canary host this
reduced one frontend from 10 to 3 processes and from about 8.9 MiB to 3.5 MiB.
A 2,000-request, concurrency-50 static benchmark completed without errors:
735 requests/second with one worker versus 751 requests/second with eight.
The roughly 2% difference is immaterial at the measured production traffic.

All four public endpoints returned HTTP 200 after this second rollout. RCON3
and RCON4 supplied the HLL Vietnam coverage; RCON1 and RCON2 supplied HLL
coverage.

The dashboard previously requested and deserialized up to 15,000 complete log
records even though it renders no more than 100 records per action plus the
matching `!admin` messages. A dedicated summary endpoint now streams the same
bounded Redis range, retains only those records, and projects only the seven
fields used by the browser. Existing live-log endpoints and their permissions
remain unchanged. On the HLL Vietnam RCON3 canary the serialized dashboard
response fell from 14.09 MB to 275.7 KB (about 98%); processing time fell from
118.7 ms to 100.0 ms. On the smaller HLL RCON1 history it fell from 93.7 KB to
36.6 KB and from 4.6 ms to 1.5 ms. The title manager also no longer forces its
30-second status and game-state polls while the browser tab is hidden; focus
refresh still supplies current data when the user returns.

The legacy `get_map_history` endpoint can contain the complete player stats,
layout and capture history for as many as 500 matches. A live RCON2 sample with
496 entries serialized to 8.88 MB; projecting all entries down to the fields
needed for a history list required only 48.6 KB. Clients that do not need match
details should use `get_map_history_summary?page=1&limit=50`. The new endpoint
defaults to 50 entries, rejects limits above 100 and reads only the requested
Redis slice. It returns numeric timestamps and leaves HLL and HLL Vietnam map
identifiers unchanged. The legacy endpoint remains response-compatible and
advertises the summary endpoint through its `Link` and `Deprecation` headers,
so existing mobile and third-party clients are not silently broken. Replacing
the observed legacy caller remains a separate client-side migration before the
8.88-MB transfer itself disappears.

This phase was canaried on RCON3 (HLL Vietnam), then RCON1 (HLL), before RCON2
and RCON4. All four backends were healthy, their public URLs returned HTTP 200
in 35-56 ms, and no new traceback, exception, or failed-operation log appeared
during the rollout window. Frontend containers remained at about 3.5 MiB RAM.
A later 30-second stability sample recorded one Redis `SCAN`, 47 idle CRCON
database clients (down from the 63-connection baseline), and no client `idle in
transaction`. The four public responses completed in 39-62 ms and the host
still had about 16 GiB available memory.

## Admin UI delivery

The admin router previously imported almost every page before the first screen
could render. The initial bundle therefore included specialist configuration
editors, charts, player-management forms, release-note Markdown rendering and
the player-detail drawer even when none of them was open.

Routes now load their component, loader, action and route-specific error UI on
demand. Release notes load only when the About dialog needs them, and the
player-detail drawer loads on its first use. Font Awesome and Lodash imports
also use their individual modules so the bundler does not retain complete icon
or utility indexes.

| Fake-mode entry bundle | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| Minified JavaScript | 4,806.55 kB | 957.43 kB | 80.1% |
| Gzip estimate | 1,367.11 kB | 320.15 kB | 76.6% |

Fake mode is used for the before/after comparison because it provides the same
deterministic application and data path on both revisions. It includes Mirage
and Faker, which production does not ship. The final production build measured
374.84 kB raw / 114.69 kB gzip for its entry chunk. Including every JavaScript
file referenced by the initial HTML, the production load measured 1,187.09 kB
raw / 397.00 kB gzip.

`npm run check:bundle` verifies the generated `dist/` directory and fails when
the entry or complete initial JavaScript set exceeds its recorded budget. This
prevents a future route import from silently returning the application to one
large startup bundle. Deferred route chunks remain outside that initial budget
and are still covered by the route smoke and accessibility tests.

## Host-level load outside the suite

Measurements must keep CRCON cost separate from colocated consumers. On the
RCON1-4 host, `/opt/stats_discord_bot/.venv/bin/python -m hll_stats_bot`
consumed about 38% CPU and 2.2-2.7 GiB RSS during the final canary. Its
`hll-stats-discord-bot/0.1.0` client continuously paged through historical
scoreboard maps and requested map scoreboards. A second remote client also
polls game state, detailed players, live scoreboards and recent logs. The
immutable scoreboard cache and bounded default recent-log response reduce the
server-side cost of those calls, but the external bot's own CPU and memory are
not part of the RCON Suite. It requires a separate optimization and rollout
scope rather than an incompatible API change hidden in this phase.

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

The optional `config/supervisord_combined.conf` additionally groups eight
compatible, I/O-bound per-gameserver loops in one Python runtime: expiring VIPs,
live statistics, autobalancer, blacklist commands, log persistence and routine
jobs, plus auto settings and automatic broadcasts. Each loop runs in its own
monitored thread and is restarted independently after an exception. The RCON
controller already maintains one connection per thread. Auto settings and
broadcasts use cooperative waits, so the existing individual service controls
can stop them without terminating the shared process. Log ingestion, Automod,
scoreboard and RQ remain separate. Automod deliberately retains its own process
because its stricter command-log level is process-scoped and must not suppress
diagnostics for unrelated shared services.

The service API expands those threads back into the original Supervisor service
names. The settings UI therefore retains individual status and start/stop
controls even though the processes share an interpreter. Each loop accepts a
cooperative stop event; stopping the autobalancer also releases its leader
lease. Redis control values are normalized from either bytes or strings because
the application's shared Redis pool can be initialized in either mode.

The mode was canaried first on RCON3 (HLL Vietnam), then RCON1 (HLL), before it
was expanded to RCON2 and RCON4. `live_stats_refresh` was stopped and restarted
on both game types: the shared runtime fell from seven to six threads and
returned to seven, the service API reported each transition, and the public
RCON remained HTTP 200. No new runtime exceptions were logged.

| Instance | Game | Split supervisor | Shared supervisor | Reduction |
| --- | --- | ---: | ---: | ---: |
| RCON1 | HLL | 1.392 GiB | 0.966 GiB | 0.426 GiB (31%) |
| RCON3 | HLL Vietnam | about 1.13 GiB | 0.680 GiB | about 0.45 GiB (40%) |

RCON2 and RCON4 measured 0.757 GiB and 0.678 GiB respectively shortly after
their rollout. All four public endpoints returned HTTP 200 in 33-37 ms. The
mode remains opt-in until the long observation window is complete. Never enable
it while the eight corresponding individual Supervisor programs are also running.

Supervisor startup records whether an instance last used the split or shared
topology. A real split-to-shared transition resets stale per-service controls
to `RUNNING`, matching the autostart behaviour of a recreated split Supervisor.
Subsequent shared-to-shared restarts retain intentional per-service stops. This
prevents an old canary's Redis state from silently disabling a service when the
shared runtime is enabled again later.

Auto settings and broadcasts were added in a second, separately tested canary.
RCON3 fell from 715.7 MiB to 496.8 MiB and RCON1 from 1.013 GiB to 801.3 MiB.
The four supervisors together fell from roughly 3.26 GiB to 2.35 GiB, saving an
additional 910 MiB. The final RCON2 and RCON4 samples were 563.7 MiB and 492.1
MiB. Direct stop/start canaries for RCON1 auto settings and RCON3 broadcasts
changed the shared process from nine to eight threads and back to nine while
preserving the requested state. All services subsequently reported `RUNNING`,
all four public URLs returned HTTP 200 in 34-51 ms, and no new supervisor error
was logged.

## Configuration

All settings are optional and existing installations receive conservative
defaults.

## Container resource budgets

The deployment templates now give every per-server backend and supervisor an
explicit resource envelope. These values are intentionally above the measured
warm figures: a limit is a fault-isolation boundary, not a target to run at.
Docker stops an over-limit process instead of allowing one problematic CRCON
instance to evict unrelated instances on the same host.

| Service | CPU limit | Memory limit | Reservation | Why |
| --- | ---: | ---: | --- | --- |
| Per-server backend | 1.0 CPU | 1024 MiB | 0.10 CPU / 256 MiB | 316-571 MiB observed after warmup; leaves controlled headroom for requests and imports |
| Per-server supervisor | 1.5 CPU | 2048 MiB | 0.20 CPU / 512 MiB | split runtime observed at 1.11-1.41 GiB; protects the host while preserving recovery headroom |
| Webhook service | 1.0 CPU | 512 MiB | 0.10 CPU / 128 MiB | delivery is I/O-bound and the queue has its own bounded retry policy |
| Mobile/Discord worker | 0.5 CPU | 512 MiB | 0.05 CPU / 128 MiB | isolates remote relay/API latency from game administration |

The variables `BACKEND_CPU_LIMIT`, `BACKEND_MEMORY_LIMIT`,
`SUPERVISOR_CPU_LIMIT`, `SUPERVISOR_MEMORY_LIMIT`, `WEBHOOK_MEMORY_LIMIT`,
`BACKGROUND_WORKER_CPU_LIMIT` and `BACKGROUND_WORKER_MEMORY_LIMIT` override
these defaults. Do not raise a limit in response to a single OOM without first
capturing the container's `docker stats`, service logs and the active server
count.

`backend_*` and `supervisor_*` use `restart: on-failure:5`. A process that
repeatedly exits or is OOM-killed is therefore contained after five retries
instead of consuming host CPU indefinitely. Fix the cause, then restart only
the affected service with `docker compose up -d backend_N supervisor_N`.

### Four-server production revalidation

The budget proposal was rechecked against a read-only `docker stats` sample
from the live four-profile host on 2026-08-21. The host had 31 GiB RAM, about
17 GiB available memory and a load average of 1.40 at capture time. The
profiles were serving both HLL and HLL Vietnam.

| Component | Per-profile observation | Four-profile total |
| --- | ---: | ---: |
| Backends | 313-567 MiB | 1.69 GiB |
| Supervisors | 632-934 MiB | 2.90 GiB |
| Backends + supervisors | 0.95-1.50 GiB | 4.59 GiB |
| Shared CRCON delivery workers | — | 282 MiB |

This confirms that the 1 GiB backend and 2 GiB supervisor limits retain
meaningful burst/recovery room while establishing a hard isolation boundary.
The baseline was captured before these new template limits are deployed, so
the values are an input to the rollout rather than evidence that Docker has
already enforced the limits.

### Capacity profile and measurement procedure

The following is a capacity envelope for CRCON application containers only. It
does **not** include the gameservers, PostgreSQL disk/cache, Redis, Nginx, the
host operating system or a safety margin; provision those separately. The
four-instance figures are validated canary measurements above. Frontline's
supported deployment envelope ends at **four CRCON profiles per host**. The
legacy `docker-templates/ten-servers.yaml` remains a reference template; it is
not a supported Frontline capacity profile and must not be deployed without a
separate engineering and capacity plan.

| Profile | Backends + supervisors (limit envelope) | Shared workers (limit envelope) | Required measurement before production |
| --- | ---: | ---: | --- |
| 1 gameserver | 3.0 GiB / 2.5 CPU | 1.5 GiB / 2.0 CPU | idle, normal admin use, webhook burst |
| 4 gameservers | 12.0 GiB / 10.0 CPU | 1.5 GiB / 2.0 CPU | baseline canary plus concurrent dashboard and Discord actions |

For each profile, capture five minutes of idle and five minutes of a
representative event burst. Run `docker compose config` first to confirm the
resolved limits, then sample `docker stats --no-stream` every 30 seconds and
record `docker inspect` values for `Memory`, `MemoryReservation` and
`NanoCpus`. Test both HLL and HLL Vietnam, including a webhook/Discord event,
before moving from 1 to 4 gameservers. Existing dynamic four-profile
installations must add
`docker-templates/four-server-resource-limits.override.yaml` after their
existing Compose overrides so the budget is enforced by Docker as well as
documented by the templates.

| Variable | Default | Purpose |
| --- | ---: | --- |
| `HLL_DB_POOL_SIZE` | `1` | Persistent SQLAlchemy connections per supervisor process |
| `HLL_DB_MAX_OVERFLOW` | `2` | Temporary connections allowed during a short burst |
| `HLL_DB_POOL_RECYCLE` | `900` | Seconds before a retained connection is recycled |
| `HLL_API_SERVER_MODE` | `split` | `unified` is an opt-in low-memory ASGI mode; split Gunicorn + Daphne retains higher concurrency |
| `HLL_GUNICORN_PRELOAD` | `auto` | Preload for multiple API workers; disabled automatically for one worker |
| `HLL_GUNICORN_MAX_REQUESTS` | `1000` | Recycle a split Gunicorn worker after this many requests; zero disables recycling |
| `HLL_GUNICORN_MAX_REQUESTS_JITTER` | `100` | Random extra requests before recycling to stagger instances |
| `HLL_SUPERVISOR_CONFIG` | `/config/supervisord.conf` | Set to `/config/supervisord_combined.conf` for the opt-in shared supervisor runtime |
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
only the maximum bounded work set and deletes in separately committed batches.

### Server-scoped log history index

Production `EXPLAIN (ANALYZE, BUFFERS)` measurements on 18.45 million
`log_lines` rows showed that the event-time-only index had to discard 22,211
rows from other servers to find one server's newest event. A one-day history
query read 11,048 shared buffers and discarded 34,015 rows to return 16 rows.

Migration `c9e1f4a7b2d6` adds the non-unique
`ix_log_lines_server_event_time(server, event_time)` index. It is created and
dropped concurrently so log ingestion remains writable while PostgreSQL builds
or removes it. The existing event-time index stays available for intentionally
cross-server queries, and the `unique_log_line(event_time, raw)` constraint is
not changed. The migration therefore changes no gameplay data and no dedupe
semantics.

#### RCON1-4 rollout validation

The migration was deployed to RCON1-4 in release `v0.4.13.16`. On 2026-08-26,
the production index was valid and ready, occupied 554 MB and had already served
6,514 scans. No index build was still running and PostgreSQL reported zero
deadlocks.

RCON2-4 immediately selected the composite index. Fetching the newest 1,000
server rows took 0.7-0.9 ms. RCON1 exposed a data-distribution edge case: it owns
17.64 million historical log rows but had no current-day rows, so PostgreSQL
misestimated `server = ? ORDER BY event_time` and selected the global time
index. That plan discarded 635,013 rows from other servers, touched 222,964
buffers and took 327 ms.

Release `v0.4.13.17` expresses server-scoped reads as the equivalent bounded
range over `(server, event_time)` and orders by both index columns. The final
production plan returned 1,000 complete RCON1 log rows in 2.04 ms from 336
buffers, a 99.4% latency reduction and 99.85% fewer buffer accesses for the
measured worst case. RCON2-4 continued to return the correct server-local rows.
The composite index scan counter increased from 6,514 to 7,051 during rollout
and validation.

Operational checks after the `v0.4.13.17` rollout:

- all RCON1-4 frontends reported `v0.4.13.17` and HTTP 200;
- all RCON1-4 backends, supervisors, the combined background worker,
  maintenance, PostgreSQL and Redis were healthy;
- all required supervisor processes were `RUNNING`; optional disabled jobs
  remained intentionally `EXITED` on the instances where they are not enabled;
- application logs contained no new traceback, fatal or process-spawn errors;
  two webhook 404 messages belonged to an already deleted external webhook and
  were purged by the existing queue handling;
- Redis added no `SCAN` or `KEYS` calls during the observation window, with zero
  evictions and zero rejected connections;
- three post-rollout samples kept application containers inside their configured
  limits. Backend memory was 313-398 MiB of 1 GiB, supervisors 612-910 MiB of
  2 GiB and the combined worker 168 MiB of 512 MiB. PostgreSQL's temporary
  increase in Docker memory was file cache created by the deliberate worst-case
  baseline scan (`anon` 74 MB, `file` 3.41 GB), not additional process heap.

Rollback remains available through the verified database dump
`postgres-20260826T232512Z-1a5de7f6813a-to-3100925db611.dump`, its SHA-256
sidecar, deployment state `20260826T232512Z.env`, and the local backend and
frontend images tagged `rollback-1a5de7f6813a`. The rollout did not target
ente1, ente2, hll1 or any other installation.

Do not enable `HLL_LOG_RETENTION_DAYS` until the affected raw game events have
an approved archival path. `log_lines` is the source for round-stat generation,
historical player logs, stat reprocessing, and the autobalancer history
fallback. Existing `PlayerStats` rows survive deletion, but the source data can
no longer be reconstructed. Application, error, and container logs are outside
this command's scope.

Deployment-backup retention can be reviewed independently with the read-only
storage planner:

```bash
python scripts/plan_storage_hygiene.py --keep-latest 8 --keep-weekly 8 --keep-monthly 6
```

The planner never changes or moves files. It protects every backup referenced
by `.deploy-state/*.env`; its candidates are review output, not an instruction
to delete them. Files and directories outside the managed `postgres-*.dump`
set are reported separately with their complete size and are never selected as
candidates.

```bash
python rconweb/manage.py runtime_data_retention \
  --audit-days 365 --batch-size 1000 --max-batches 10

# Only after reviewing the dry-run and taking a backup:
python rconweb/manage.py runtime_data_retention \
  --audit-days 365 --batch-size 1000 --max-batches 10 --execute
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

## Live roster polling baseline

The production frontend already requests `get_team_view?compact=true`. A
read-only measurement on 2026-08-27 confirmed that the bounded live projection
is materially smaller than the full player profile. RCON3 had nine online
players during the usable sample; RCON1, RCON2 and RCON4 were empty.

| RCON3 projection | SQL statements | Profile JSON | Profile gzip | Time |
| --- | ---: | ---: | ---: | ---: |
| Full profile | 11 | 19,393 B | 2,675 B | 19.75 ms |
| Compact live profile | 7 | 3,585 B | 759 B | 8.01 ms |

The complete team-view payload was 25,837 B (3,713 B gzip) in full mode and
10,039 B (2,031 B gzip) in compact mode. The direct team-view timings were not
compared because the full result was already cached while the compact result
was cold. No player data was exported by the measurement.

The remaining frontend issue was overlapping observers for the same React
Query key. `GlobalState` registered a 30-second roster interval while the Live
and Teams pages registered 10-second intervals and Live Sessions registered a
15-second interval. Because route navigation starts the page timer at an
arbitrary offset, the global timer can add two avoidable HTTP requests per
minute and active browser. The modeled request budget is therefore:

| Route | Before | After local change | Maximum reduction |
| --- | ---: | ---: | ---: |
| Live / Teams | up to 8/min | 6/min | 25% |
| Live Sessions | up to 6/min | 4/min | 33% |

The local change keeps `GlobalState` subscribed to the shared query so its
online-player state still updates, but disables its own interval on pages that
already own a faster roster observer. Dashboard and player-record routes keep
the global 30-second interval because they have no page-owned roster poll.
Contract tests cover trailing slashes, every page-owned route and the routes
that must retain global polling. The polling-budget check, 13 focused API
contract tests and the production frontend build passed. This change is not
yet released or deployed; per the release policy it will be bundled with other
validated low-risk optimizations before a requested RCON1-4 rollout.

### Shared player-action menus

The Live player table already used one page-level `ActionMenu`, but the Teams
and Live Sessions views still mounted a complete `ActionMenuButton` for every
rendered player. Each instance constructed its own MUI menu and subscribed to
authorization, action-dialog, profile-sidebar, account-edit and soldier-edit
hooks even while its menu was closed. With a full 100-player roster, opening
all squads could therefore create up to 100 copies of that menu and hook tree
on either page.

The local change keeps one lightweight trigger per player and delegates it to
exactly one shared row-action menu per page. The selected recipient and anchor
element are stored at page level. Multi-player selection toolbars remain
separate because they represent a different action target and are mounted only
once. Functional behavior is unchanged: Teams retains profile and edit menu
entries, while Live Sessions retains the existing online-player actions.

| Rendered roster | Complete row-action menus before | Complete row-action menus after | Reduction |
| --- | ---: | ---: | ---: |
| 1 player | 1 | 1 | 0% |
| 50 players | 50 | 1 | 98% |
| 100 players | 100 | 1 | 99% |

This is a component-mount reduction, not a claim that total page CPU or memory
falls by the same percentage. A static contract rejects full per-row action
menus on Live, Teams and Live Sessions. Three focused browser tests verified
that the shared menu opens from a Teams row, a Live Sessions desktop row and a
Live Sessions mobile card. The production frontend build also passed. This
change is not yet released or deployed and will be included only in a later,
explicitly approved bundle.

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

To roll back the shared supervisor runtime, restore the regular
`config/supervisord.conf` (or the previous combined config) and recreate only
the affected supervisor container. Do not start standalone auto-settings or
broadcast processes while their same-named shared threads are running; the
normal and combined configs are mutually exclusive by construction.

Database retention and index replacement require their own migration, backup
and rollback plans. Process consolidation must be canaried separately from
database lifecycle work.
