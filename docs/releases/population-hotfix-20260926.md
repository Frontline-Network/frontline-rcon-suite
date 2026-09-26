# Population history test hotfix — 2026-09-26

The user requested a test rollout to HLL1 and RCON3/4. The population-history API
and recorder from commit `c25479e322739f53204908dff0a79eba61a2a68e` were deployed
as an overlay on each installation's existing v0.8.7/Conquest hotfix image.
The feature remains in draft [PR #255](https://github.com/Frontline-Network/frontline-rcon-suite/pull/255);
this rollout does not merge the PR or publish a release.

## Result

Verified at approximately **2026-09-26 01:27 UTC / 03:27 Europe/Berlin**.
Counts below are the verification snapshot, not an analysis of seeding outcomes.

| Instance | Recorder topology | First recorded slot (UTC) | Successful / failed samples |
| --- | --- | --- | --- |
| hll1.fln.gg | separate Supervisor process | 2026-09-26T01:20:00Z | 15 / 0 |
| rcon4.fln.gg | shared runtime | 2026-09-26T01:24:00Z | 7 / 0 |
| rcon3.fln.gg | shared runtime | 2026-09-26T01:26:00Z | 3 / 0 |

All backends were healthy, previously running services recovered, and the new
recorder produced fresh successful measurements. The pre-existing HLL1 scoreboard
failure also recovered after the application restart. RCON3/4 retained their
existing shared-runtime service controls. Configured legacy services that exit
normally were not treated as regressions.

The database now has Alembic head `f4b9c2d6e310` and Django migration
`0039_population_history_permissions`. Existing server settings and user/group
permission assignments matched their pre-deployment fingerprints. The only
recreated application pairs were HLL1 backend/supervisor 1, then RCON4, then RCON3.
Other CRCON containers, including PostgreSQL, Redis, the retired RCON1/2
containers and the separate Ente installation, retained their IDs and running
state. Gameservers were not restarted.

## Evidence

- All four jobs in [the deployment commit's CI run](https://github.com/Frontline-Network/frontline-rcon-suite/actions/runs/36206367321) passed, including backend/PostgreSQL concurrency tests and admin browser checks.
- Full PostgreSQL custom dumps were restored into temporary PostgreSQL containers
  before either installation's production migration. Both restored copies passed
  migrations and zero-player, query-error, missing-bucket and duplicate-sample checks.
  PostgreSQL, a fresh Redis container and the migration probe shared an isolated
  network namespace with no external network. The temporary copies were removed.
- Actual HTTP requests to each running backend verified Bearer authentication,
  raw history, minute aggregates and seeding-session reads with a temporary user
  having only `api.can_view_population_history`. Anonymous requests returned 401;
  write and cross-server attempts returned 403. Temporary users and keys were
  deleted; no test seeding markers or synthetic population samples were written
  to production.
- All 14 overlaid runtime files were hash-checked inside both application
  containers for every instance. Candidate image layers preserve the prior image.
- Public HTTPS checks passed on all three domains: version endpoint 200;
  population-history and seeding-session endpoints 401 without authentication.

## Images and recovery material

| Installation | Previous image | Hotfix image |
| --- | --- | --- |
| HLL1 | `sha256:78a49f117e9932f0494466d87becbf6e251a14690ea8dde4e880161eb350d02c` | `sha256:7d25a9c71d9812de932e570d79d3f6ef14d90a06d6afcdb31f5bfeb6251ed3eb` |
| RCON3/4 | `sha256:8d05605ea691b079671ee446e3eea34190e1c697ca3d0e63d05d8e04ed5fed96` | `sha256:d0e84f62165906a5c47086158195828b24b43bf5c816c80c2bef7713b175f8a2` |

Deployment directories, with owner-only permissions:

- HLL1: `/home/frontline/hll/srv1/hll_rcon_tool/.deploy-state/population-hotfix-c25479e3-20260926`
- RCON3/4: `/root/hll_rcon_tool/.deploy-state/population-hotfix-c25479e3-20260926`

Each directory contains `state.json` with checksums and acceptance receipts,
`postgres-before.dump`, `configuration-before.tar.gz`,
`compose.hotfix.json`, `compose.rollback.json`, migration logs and
`OPERATIONS.md`. Dump sizes were **1,272,085,247 bytes** (HLL1) and
**2,225,712,702 bytes** (RCON3/4). Previous images are also tagged
`frontline/population-rollback:hll1-c25479e3` and
`frontline/population-rollback:rcon-c25479e3`.

Use the installation's `compose.hotfix.json` for subsequent operations. An
application rollback uses `compose.rollback.json`, the same Compose project
(`fln_hll_srv1` or `hll_rcon_tool`), and only the affected `backend_N supervisor_N`
with `up -d --no-deps --no-build --pull never`. First apply the usual active-vote
and autobalancer execution gates.

Keep the additive database migration on an application rollback. Do not
automatically restore or downgrade production data. Do not restart the old
maintenance image against the new Alembic head; the new hotfix Compose file pins
maintenance to the compatible candidate image. No application rollback was needed.

## Using the API

The recorder uses the default 30-second interval and 60-day retention.
[The API guide](../population-history-api.md) documents access, query parameters
and manual seeding markers. A permanent analysis account/API key was not created
by this rollout; existing administrators can provision one with the documented
read permission. Collection starts at the timestamps above. Earlier history is
not automatically reconstructed, and connected AFK players remain part of the
server's reported occupancy.
