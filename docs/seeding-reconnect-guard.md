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

Deployment is a source-only overlay onto HLL1's actual running v0.8.5 image:
`rcon/automods/models.py` and `rcon/automods/seeding_rules.py`. No frontend,
dependency, schema, game-server, configuration or other-server change is needed.
Back up the database, configuration and previous image before replacing only
HLL1 `backend_1` and `supervisor_1`; verify in a network-isolated candidate first.
