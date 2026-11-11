# RCON3/4: report-context and session hotfix, 2026-11-11

## Code and validation

- Commit: `453ba19202bf3bdfd29863d6c2a3facabbc3246b`.
- Base: existing `v0.9.4-rc.1`, image `sha256:0f32239659411feef26726df7d34211603581ba16e3167506f9ccae445e6cc52`.
- Candidate image: `sha256:073d7ca1ed734850923c8075956749f7fab94f4c8cdc85ecb52c4745429ce106`.
- 353 isolated pytest cases passed: report admin, API, evidence, communication, members, semantic reason handling and session accounting. Test containers have no production network access and perform no real player actions.
- The deploy helper verifies that production source hashes equal the final tested hashes; smoke checks also run inside the actual minimal hotfix image.

Initial live-context failures now retain runtime ownership and an unsent report for at most 15 seconds, without extending the original report deadline. Fresh context still must pass round, identity, session, configuration and admin-ownership checks. Errors after the durable sending marker retain the existing unknown/no-retry behavior. Recovery messages no longer incorrectly assert that the service restarted.

Session accounting orders session evidence independently from combat processing. CONNECT precedes activity with the same timestamp, and exact duplicate CONNECT/DISCONNECT boundaries are counted once. The existing warmup/cooldown policy is unchanged. There is no schema migration or historical data rewrite.

## Investigated cases

All times below are UTC on 2026-11-10.

- Report event 5263: communication report at 14:02:17; the round ended at 14:02:27. Context was unavailable during processing at 14:02:39. Manual review is the correct result after this round change; the historical report must not be replayed. The previous error additionally discarded runtime ownership and misreported a restart.
- Round 22567, first session case: CONNECT 18:26:20 to DISCONNECT 18:29:37, then CONNECT 18:31:44 to DISCONNECT 18:31:54. Total 197 + 10 = 207 seconds. A repeated disconnect caused a transient live mismatch. Persisted time already equals 207 seconds.
- Round 22558, second session case: MESSAGE and CONNECT share 14:00:53, 94 seconds before the round ended. Processing MESSAGE first incorrectly inferred an additional session. Under the existing 100-second end-of-round discount, the stored 0 seconds is still correct. With no cooldown discount, the regression test returns the actual 94 seconds. No historical correction is justified.

## Backup and scope

Private server backup directory: `/root/hll_rcon_tool/.deploy-state/hotfix-report-sessions-20261111`.

- PostgreSQL: 3,684,806,306 bytes; TOC and complete archive decoding checked.
- Redis: 119,785,702 bytes; RDB integrity checked.
- Configuration: archive checked and fully read; source configuration hashes are guarded.
- SHA-256 verification precedes image build. Existing images are pinned with rollback tags and a rollback compose file.
- Only backend and supervisor of RCON4, then RCON3, are selected. RQ statistics workers run inside those supervisors. Frontends, shared Discord delivery, PostgreSQL, Redis, retired RCON1/2 and other installations remain outside the rollout.
- One unlabelled transient container present during the isolated test run was absent before and after it. Its exclusion from the inventory comparison is documented in the private state; production-service guards remain intact.

Rollout completed in order RCON4, then RCON3. All four backend/supervisor containers run the tested hotfix image and matching source hashes. Public HTTPS endpoints pass; required supervisor processes match the healthy baseline. Configuration, permission and other-container guards pass. No rollback was needed.

Post-start checks show fresh live snapshots (RCON4: 3.6 seconds; RCON3: 7.5 seconds), active AI configuration and no new errors in checked runtime/API/worker logs. Both servers were empty during the check. No new reports or completed rounds had arrived after deployment, so natural-report and populated-round validation remains pending. Existing inactive helper processes retain their expected exit state.
