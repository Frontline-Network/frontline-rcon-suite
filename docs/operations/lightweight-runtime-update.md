# Lightweight runtime update contract

The next Frontline RCON update migrates standard installations to the shared
Supervisor runtime and combined Frontline background worker. The objective is
lower per-instance memory without disabling any RCON feature.

## Upgrade behaviour

- New one- and multi-server templates use
  `/config/supervisord_combined.conf` by default.
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
  data rollback.

No production database, Redis keyspace or historical record is deleted by this
topology migration.
