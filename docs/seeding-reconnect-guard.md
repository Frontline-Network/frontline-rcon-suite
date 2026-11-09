# Seeding: reconnect protection

## Incident and cause

On HLL1 on 2026-09-19, a player reconnected after 32 seconds and resumed the
Allied commander role on Sainte-Marie-du-Mont. The game first reported a
stationary enemy-HQ placeholder, then the real Allied-HQ position. The automod
warned the player although nearby tactical samples were in the allowed area.
No punishment or kick was found in the inspected two-hour window.

Squad watches survive for 120 seconds and were bound only to player ID and map.
The previous connection's movement proof therefore made the reconnect's bogus
HQ position eligible for enforcement. An in-memory replay reproduced this;
the installed map-direction correction itself was correct.

## Narrow fix

- Bind positional spawn proof to the existing profile session count and a
  short-lived connection marker written by the existing connected-event hook.
- The marker also covers briefly cached profiles. The profile counter covers
  missed connected events. Marker expiry alone does not reset a valid watch.
- Re-arm first-position protection and clear that player's excursion and
  escalation state when the context changes; leave other players untouched.
- Re-arm legacy persisted watches once, without a database migration.
- Do not fall back to old offense points on a reconnect sample without position.
- Preserve map geometry, ordinary movement detection, the commander exception
  to squadless-player filtering, and configured warning/punishment/kick limits.

Regression tests replay the incident coordinates and cover both teams, regular
squads and commanders, HLL and HLLV geometry, profile/hook detection independently,
marker expiry, old watch objects, and genuine violations after respawning.

The September deployment was a source-only overlay onto HLL1's running v0.8.5 image:
`rcon/automods/models.py` and `rcon/automods/seeding_rules.py`. No frontend,
dependency, schema, game-server, configuration or other-server change is needed.
Back up the database, configuration and previous image before replacing only
HLL1 `backend_1` and `supervisor_1`; verify in a network-isolated candidate first.

## Follow-up: cached coordinates before the HQ placeholder (2026-10-15)

A second HLL1 incident on Sainte-Mere-Eglise Night exposed a different sequence:
the connection marker and profile session changed while RCON still returned the
previous connection's coordinates. A stationary, implausible enemy-HQ position
then replaced them. The old guard treated that single change as movement and
allowed escalation. The nearby tactical sample was already inside the allowed
area when the punishment was recorded. The samples establish a data-quality
problem, not the player's physical presence at that HQ.

The follow-up fix adds conservative spawn/continuity evidence:

- Require at least one metre of movement between nearby observations before
  enforcing a new spawn. The initial confirmation is limited to 500 metres;
  a larger jump becomes a new anchor, not proof of movement. This also applies
  to the first non-zero position after `(0, 0, 0)`.
- Once confirmed, allow up to 100 metres/second, with a five-second allowance
  for the normal polling/cache cadence. This is a generous continuity check
  for infantry and vehicles, **not** a speed-cheat detector.
- Re-arm after an implausible jump, a death-counter change, missing/invalid
  coordinates, a gap exceeding 30 seconds, or a backwards clock adjustment.
  A pending stationary HQ placeholder never becomes trusted merely by waiting.
- Discard that player's previous positional escalation on loss of proof.
  Repeated unspawned samples do not reset unrelated role warnings every poll.
- While known positional evidence is unavailable/untrusted, do not switch to
  offense-point punishment. The existing fallback remains available on servers
  that never supplied positions and for unknown map geometry after spawn proof.
- Persist the last observation in the existing Redis watch. Older pickles are
  re-armed lazily; no database migration or configuration change is required.

Regression coverage includes the recorded old-position/HQ/spawn sequence with
profile and hook reconnect signals independently, with and without death
counters, level-one players, HLL/HLLV movement, real boundary crossings,
stationary offenders after proof, respawn, data loss, clock/gap handling, map
changes, legacy pickles and isolation from other players' escalation state.

This is deliberately fail-safe: stationary players first seen outside the
boundary are not punished until movement confirms the spawn. No available RCON
field conclusively proves that a player has physically spawned; the guard does
not claim otherwise. Production deployment requires separate approval.
