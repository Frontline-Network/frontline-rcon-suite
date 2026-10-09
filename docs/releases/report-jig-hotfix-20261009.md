# Squadleader report interpretation hotfix

The shared Discord AI service was updated for RCON3/4 on **2026-10-09**.
Verification completed at **15:04 UTC / 17:04 CEST**. Source commit:
`7eff586fa2ad15261996c5ccc2a7220a676a52e6`. Public version remains **v0.9.2**;
no GitHub release, tag or push was made.

## Cause and correction

The 16:24 CEST RCON3 report `!admin jig not talking` remained manual because
the model incorrectly claimed that no leader was identified. The stored roster
contained an own-team Jig squadleader with a correctly normalized role. The
independent target resolver accepted the correct squad interpretation. In that
snapshot the reporter was also the own-team leader; the opposite team's Jig
leader was not an eligible alternative. The old report was not replayed.

Prompt version `report-reason-4` explicitly defines bare squad communication
reports as referring to the squadleader of the reporter's team. Neither `SL`
nor `squad` is required. This applies to all recognized squad labels, not only Jig.
A compact own-team leadership index is derived from supplied normalized roles,
with squad members, leader names and missing role normalization distinguished.
Multiple leaders remain visible rather than silently choosing one. Alphabet
guidance includes Jig/Juliet/Juliett and the other supported squad aliases.

The entire reason is still interpreted. Retractions, negations, mixed allegations,
missing leaders and conflicting targets remain manual. Original/fresh roster
checks, team/role/session guards and the self-report setting are unchanged.
The configured model, active real-kick mode and all server settings are unchanged.

## Tests and production checks

- **312 backend/resolver tests** and **124 Discord service tests** passed.
- All **14 synthetic real-model cases** passed with rosters of 98–101 players:
  self/member/other-leader reports, opposing same-name squads, German/English,
  varied word order, aliases, other bare squad names, player names and negative
  cases. Maximum observed response time was 12.33 seconds.
- Independent resolution of all 14 returned decisions passed in a network-isolated
  container, including enforcement of the self-report setting.
- Installed source hash, expected image, unchanged environment and configurations,
  active AI mode and one Report-Admin owner per RCON passed.
- Discord service, guild binding and callback reported online. Both public RCONs
  passed HTTPS and CSRF/no-store checks.

No test player messages, live incidents, kicks or bans were generated. Evaluation
used the analysis-only endpoint with synthetic data. A naturally submitted report
is still needed to confirm a new complete live moderation action.

## Deployment and recovery

Only `discord_service/app/report_reason.py` changed in the deployed image:
`sha256:ddcb101474019f44c916cc302589718cde89d8de8513bcb26ac259834fd6116e`.
RCON3/4 backends, supervisors, frontends, shared workers, database containers and
game servers were not restarted. All other containers retained their IDs and
running states. Original Compose files and settings were not overwritten.

Private backup/state directory:
`/root/hll_rcon_tool/.deploy-state/report-jig-20261009/`.
Its configuration/state files contain credentials and must not be published.

- `central-postgres.dump`: 376,669 bytes; SHA-256
  `aca601a21d77de1c83bce9e7dad08eaa134899579d114dc83c0bf3f4df2d5625`.
  The entire archive was read by `pg_restore` before the update.
- `configuration-before.tar.gz`: SHA-256
  `3cdf5e03c07612943e3764adf827a4f029ee3c75fb36b048d32893d0bb7bb736`.
- `rollback.json` restores the prior central image, also retained as
  `frontline/report-jig-base:20261009`. `hotfix.json` is the active central model.

Cutover checked for pending Report-Admin work under the RCON3/4 action locks.
Rollback uses project `frontline-discord-service`, its original project directory,
the private rollback model and only service `service`, with
`up -d --no-deps --pull never`. Coordinate pending work under the same locks.
No schema migration or full database restore is needed; retain incident history
and do not replay previous reports or restart unrelated/retired services.
