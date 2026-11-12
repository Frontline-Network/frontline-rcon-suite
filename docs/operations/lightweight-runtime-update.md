# Lightweight runtime update contract

The next Frontline RCON update migrates standard installations to the shared
Supervisor runtime, combined Frontline background worker and adaptive API
runtime. The objective is lower per-instance memory and fewer idle processes
without disabling any RCON feature.

## Upgrade behaviour

- New one- and multi-server templates use
  `/config/supervisord_combined.conf` by default.
- The phase-two combined configuration contains only three Supervisor programs:
  `frontline_runtime`, the RQ `workers`, and `cron`. The shared runtime exposes
  18 logical services through the existing service API, including logs,
  campaigns, scoreboard, Automod, seed VIP and VIP rewards.
- `FRONTLINE_SUPERVISOR_RUNTIME_MODE=auto` migrates an empty setting and the
  standard split configuration to the combined configuration.
- A non-standard Supervisor path is preserved in `auto` mode. Operators must
  choose `combined` explicitly to replace it.
- `FRONTLINE_SUPERVISOR_RUNTIME_MODE=split` selects the former process layout
  as the supported rollback.
- `FRONTLINE_BACKGROUND_WORKER_MODE=auto` selects the combined worker. Split
  delivery workers are stopped before the combined worker starts, so the same
  outbox cannot be consumed twice.
- The deployment state file records both selected topologies and the exact
  database backup used for rollback.
- `HLL_API_SERVER_MODE=auto` serves HTTP and WebSockets from one Daphne process
  when `NB_API_WORKERS=1`. Multiple API workers retain the split Gunicorn and
  Daphne topology automatically. `HLL_API_SERVER_MODE=split` is the explicit
  compatibility rollback and does not require a migration or data restore.
- Backend, Supervisor and frontend entrypoints replace their setup shell with
  the long-lived daemon. Daphne, Supervisord and Nginx therefore become PID 1
  and receive Docker stop signals directly. Roll back this process-only change
  by restoring the previous backend and frontend image references from the
  deployment-state Compose model.

## Measured HLLV canary

RCON3 ran the exact candidate commit with a verified PostgreSQL dump, Redis
snapshot, configuration archive, rollback Compose model and SHA-256 manifest.
After warm-up the three core containers used about 435 MiB in total and had
seven long-lived processes: one Daphne process, Supervisord plus Cron, the
combined runtime and RQ worker, and an Nginx master plus worker. RQ temporarily
adds one child while executing a queued job, so seven idle and eight busy are
both valid states.

The canary kept all 18 logical services running, reported zero container
restarts and no relevant tracebacks, and completed 100/100 bounded health
requests at about 190 requests/second with a 53.6 ms p95. Both API listener
ports and the public root and health endpoints remained available.

## Measured HLL canary

HLL1 ran the same candidate commit after a fresh verified 1.2 GiB PostgreSQL
dump, Redis snapshot, configuration archive, exact rollback Compose model and
locally reload-tested rollback images. After warm-up the three core containers
used about 399 MiB in total, down from about 581 MiB before the switch (roughly
31%). Their long-lived process count fell from 13 to seven.

All 18 logical services remained running, the live HLL game-state probe
returned the current map and player counts, public root and health requests
returned HTTP 200 in about 5 ms, and the three replaced containers reported no
restart or relevant fatal log marker. The HLL rollback set is stored under the
instance deployment state alongside checksums for the before and after
evidence.

## Acceptance gate

Before publication, validate an upgrade from the previous release using an
isolated restored database and Redis snapshot. Then canary one HLL Vietnam and
one HLL installation with fresh verified backups. Acceptance requires:

- every logical service remains visible and controllable through the existing
  service API;
- no duplicate background delivery, campaign message, VIP grant or RCON
  action;
- live logs, scoreboard, Automod, broadcasts, campaigns, Autobalancer, VIP
  lifecycle and configured Discord/mobile delivery remain operational;
- no new restart, OOM or migration error;
- measured Supervisor and delivery-worker RAM is lower than the split baseline;
- Redis control traffic uses batched reads and transition-only state writes;
- explicit split rollback restores the previous topology without a schema or
  data rollback;
- Daphne, Supervisord and Nginx are PID 1 and no idle entrypoint shell remains;
- the normal process baseline is seven when RQ is idle and eight while its
  single work child is active;
- repeated stop/start/restart checks cover every migrated logical service,
  including a scoreboard restart from a different runtime thread;
- database-pool timeouts and shared-runtime tracebacks remain absent under the
  HLLV/HLL canary workload.

No production database, Redis keyspace or historical record is deleted by this
topology migration.
