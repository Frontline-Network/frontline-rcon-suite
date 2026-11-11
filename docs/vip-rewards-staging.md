# VIP rewards staging verification - 9 November 2026

## Result

**11/11 isolated PostgreSQL integration tests passed.** The existing local
regression selection also passed: **119 tests** (VIP rewards, log parsing and
seeding rules).

All seven new reward types were enabled in live-write mode in the test database,
with the central seeding pause enabled. During ten minutes of simulated seeding:

- No VIP writes and no player notifications occurred.
- No new grant records were created.
- No attendance, event, challenge or milestone progress accumulated.
- Seed-VIP being disabled did not disable the seeding gate.

Additional checks passed:

1. No release before the full five-minute stability period.
2. No delayed payout of kills received during seeding.
3. A population drop blocks even kills queued while the server was previously live.
4. Already queued awards are skipped when delivery encounters the seeding gate.
5. Failed and stale status observations stop awards.
6. Changed Seed-VIP population targets restart the gate before queued events are
   processed; no hidden challenge progress is consumed.
7. Explicitly disabling the seeding pause allows awards; the default remains on.
8. Seed-VIP's existing reward function still grants its reward independently of
   the additional-reward pause.
9. Two concurrent delivery workers use real PostgreSQL advisory locks and both
   increments are retained without overwriting each other.
10. The new migration upgrades and downgrades successfully on PostgreSQL 12.

## Isolation and evidence

RCON3 is a live HLL Vietnam installation, not an empty staging instance. A
read-only preflight reported 97 players. No application code, configuration,
database schema, VIP entry or service was changed in that installation.

Tests ran alongside it in temporary, resource-limited containers with an internal
Docker network, no published ports, no production mounts or production credentials,
and a dedicated `viprewards_staging` PostgreSQL database. `RecordingRcon` terminated
all game-server calls locally. Time advancement and player populations were
synthetic; the ten-minute and five-minute scenarios did not use wall-clock waiting.

- Backend runtime: `760f29458c95aefb7a5151bce763d959775e38797a5b1a35b8c0ca06206a4025`
- PostgreSQL image: `097d7e0eba6e7120560ac2d3a7e4b2a110d219b7dcbf43c0318dce1849c9761a`
- Final source archive SHA-256: `01fd50f69f09c20eae38984ec3c7843bc2f09c0bc88a1b3269dfbde8071c710e`
- Test source: `tests/staging_vip_rewards.py`
- Local evidence directory: `Autobalancer/outputs/vip-rewards-staging-20261109/`
- Final run: `staging-final.log`; independent cleanup check: `postcheck.log`.

The final check found no remaining staging containers or networks. RCON3's backend
and the shared PostgreSQL container remained healthy, with their original image
IDs and startup timestamps.

## Corrections made during testing

- Restart seeding protection **before** consuming queued events when target
  populations change. Previously payout was blocked, but challenge progress could
  already have been recorded.
- Remove an unused `hllrcon.Faction` import, which is absent in the newer runtime.
- Keep the Seed-VIP helper's API type import under `TYPE_CHECKING`; importing a
  helper no longer loads unrelated API services and their dependencies.

## Boundaries

The initial integration run verifies reward policy, persistence, migration and
locks against real PostgreSQL. Full web/API startup was subsequently verified
as documented below. Neither run verifies the HLL network protocol, actual live
kills or production rollout. The new seeding gate reacts on its next
30-second observation; it is not an instantaneous game-server event lock.

The unchanged RCON3 runtime lacks `rq_scheduler`, which the local project's
requirements still declare. Importing the full local API on that unchanged image
therefore failed during preparation. The feature tests avoid the unnecessary
runtime API type import, but a complete deployment must build an image with this
project's declared dependencies and smoke-test its full startup first. Do not
overlay the entire local application onto the running RCON3 image.

The integration suite refuses a database name other than `viprewards_staging` or
a hostname other than `viprewards-staging-db`. Without `TEST_VIP_REWARDS_DB` it
skips execution. Run it with the repository on `PYTHONPATH`, in maintenance import
mode, using the isolated runner documented in the evidence directory.


## Full application staging follow-up

The matching staging image was built from the existing runtime with all versions
in this repository's `requirements.txt`, plus Gunicorn, Daphne and Supervisor.
`pip check` passed; the earlier missing `rq_scheduler` dependency no longer
prevents full application startup in this image. No source changes were required
in this follow-up.

A separate internal Docker network hosted disposable PostgreSQL, Redis, two
Gunicorn web workers, the actual VIP reward worker loop and Nginx serving the
production frontend build. All Alembic migrations from an empty database,
configuration seeding, Django migrations and `manage.py check` succeeded.
No production credentials, database, network or application mounts were used.
The game boundary was replaced by a synthetic adapter; the actual 30-second
worker scheduling and HTTP stack were used without accelerated time.

**22 HTTP/worker acceptance assertions passed**, including:

- Anonymous and unprivileged users cannot read protected configuration; a
  read-only user can read but cannot save it.
- Initial defaults remain disabled, in preview mode, with seeding protection on.
- Administrator validation, persistence and dated event configuration round-trip
  work through the real HTTP API.
- With all seven reward types enabled in non-preview mode and Seed-VIP itself
  disabled, the worker reports seeding at Allies 14/20 and Axis 18/20.
- Across more than two real polling intervals, injected melee kills and balance
  signups create no player progress, grant records or VIP write attempts.
- All eight injected events are processed with `allowed=false`. Their internal
  event records are intentionally retained; they are not eligible for later
  payout. The grant journal remains empty.
- Seed-VIP configuration is unchanged; a synthetic status outage changes the
  reward status to `unknown` and keeps rewards paused.
- The rewards route and production JavaScript/CSS assets are served successfully.

An actual Chrome session accessed this isolated Nginx instance through a temporary
SSH tunnel bound to local loopback. The production page displayed the seeding
pause and both team counts. Desktop and 390px viewport checks passed without
JavaScript runtime exceptions or horizontal overflow in the main content. The
other server-status widgets report offline because no real game server is
attached. The browser session and tunnel were closed after the check.

The initial acceptance assertion that no internal event records should exist was
corrected: the implementation retains those records with permanent denial flags.
This was a test expectation correction, not a reward-safety defect.

Evidence in the same local evidence directory:

- `app-stage.log`: complete application startup and 22 acceptance checks.
- `app-browser.log`, `app-browser-desktop.png`, `app-browser-mobile.png`:
  production frontend browser checks.
- `app-bundle.py`, `app-remote.py`, `app-run.ps1`, `app_*.py`, `app-browser.cjs`:
  reproducible isolated test harness.
- Full application source archive SHA-256:
  `c2060e53adec266ff1a370ef294b81c06430e679fd20d9e61b6139f83827185c`.

This remains an isolated application test, not a production deployment or a
preview observation on the live game server. A live preview run remains required
before enabling actual player rewards.

The 11 PostgreSQL integration cases were also rerun against the newly built image:
**11/11 passed** (`staging-matching-image.log`), including the full five-minute
release boundary, falling populations, queued kills/awards, stale observations,
Seed-VIP independence and concurrent delivery. Matching image ID:
`464c51df24df987dfa0aeb2e2a4df16ff80debf29e49168560ed7e47d0e321ec`.

Final independent postcheck (`app-postcheck.log`) confirmed no remaining test
containers or networks. Both temporary image tags were removed. The RCON3 backend,
supervisor and shared PostgreSQL retained their original image IDs and startup
timestamps; backend and PostgreSQL remained healthy.
