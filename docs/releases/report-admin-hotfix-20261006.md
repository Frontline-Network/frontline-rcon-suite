# Report-Admin hotfix — 2026-10-06

Deployed commit: `e11620418d975f1fab902538ab2759b5b361c02a`.
Local branch: `codex/report-admin-mvp`. No GitHub release or tag was created.
The underlying release and public version remain **v0.9.2**; the immutable
overlay images carry `gg.fln.hotfix=report-admin` and the source commit label.

## Authorized scope and behavior

The user explicitly authorized a hotfix on **RCON3 and RCON4**, activation with
real kicks, and the necessary shared Discord-service update with backup.

- New communication reports can directly kick the uniquely identified current
  own-team squadleader/commander. No vote or preliminary warning. This is based
  on a reported allegation, not proof of voice activity.
- Teamkill reports require at least five recorded teamkills in the five minutes
  before the report, restricted to the current match and the reported player.
- Conservative online-name matching supports up to three edits in longer names;
  ambiguous or short fuzzy matches remain manual. Other complaint types remain
  manual. This version is deterministic and makes no AI-provider requests.
- Both servers have `ReportAdminUserConfig.enabled=true`, `mode=active`, and
  both rules enabled. Template selection remains unset, using built-in DE/EN
  reasons. The existing leadership-vote configuration itself is unchanged;
  report-admin routing takes precedence while enabled.

Updated application services: `backend_3`, `supervisor_3`, `frontend_3`, the
corresponding three RCON4 services, and this installation's shared
`frontline_background_worker` and `webhook_service`. The separately hosted
`frontline-discord-service-service-1` received only its two affected source files.
The source comparison confirmed that its pre-existing content matched the Git
baseline after normalizing line endings.

Atomaresecho, HLL1, Ente1/2 and other hosted RCON containers were not updated.
RCON1/2 remain stopped. Game servers, PostgreSQL and Redis were not restarted.
No synthetic production reports, messages, votes, kicks or test emails were sent.

## Backups and images

Private state directory on the RCON3/4 host:
`/root/hll_rcon_tool/.deploy-state/report-admin-e1162041-20261006/`.
It contains credentials in configuration snapshots and must not be published.

| Backup | Bytes | SHA-256 |
| --- | ---: | --- |
| RCON PostgreSQL | 2350421467 | `8f47f2bb03ff725ecf3da358bf413424dea94f5db51caa16dc19623fcd0db840` |
| Discord PostgreSQL | 336479 | `77a806e3f096b2244730e366040cc02d04c448e97497d487e8adfd3454162dd2` |

Both custom-format database archives were fully read and validated with
`pg_restore`. Configuration backups and a 1447547392-byte archive of previous
images are retained alongside the private receipts. Existing SMTP credentials
and per-instance origins were preserved, including Compose dollar escaping.

Hotfix image IDs:

- Backend: `sha256:fc7bbc6e60f378ddf8b904f84804f9d36e049a1ec91e0a8a4ab9de7311e35587`
- Frontend: `sha256:d9753f777158cbbd7ed0ceae6d6c2c49eecfaf7e86ed254ac9124a473ee58303`
- Discord: `sha256:e033f2ef45bdb53d7f8879c0387536cff40766a90baddb6b643b8534f8802155`

Each overlay retains every original base-image layer. Production tracked source
and the original Compose files were not edited. Active models are
`rcon-hotfix.json` and `central-hotfix.json`; rollback models are
`rcon-rollback.json` and `central-rollback.json` in the private state directory.
Use explicit affected service names with `up -d --no-deps --pull never`.
Disable report-admin on both servers before rolling application code back.
Do not automatically restore databases, downgrade schemas, remove orphans or
reactivate retired services. No new database migration was required.

## Verification and rollout observations

- 481 backend/API tests and 85 Discord-service tests passed. Production frontend
  build, CSRF request contract and English completeness checks passed.
- Candidate imports and checksums passed in isolated, network-disabled
  containers. The first import probe lacked a writable temporary log directory;
  the corrected probe used tmpfs while retaining the read-only root filesystem.
- The backed-up PostgreSQL schema was restored to an isolated PostgreSQL 12
  container. Synthetic-only tests passed for advisory locking, event JSON,
  idempotency, restart recovery and server separation. That temporary database
  and its anonymous volume were removed; the backups were not removed.
- Discord and the shared workers were updated before the RCON canary. The first
  RCON4 attempt rolled back when the immediate Supervisor readiness check failed.
  After adding bounded process-readiness retries, RCON4 and then RCON3 passed.
  Vote and balance execution guards covered the application replacements.
- Only after both servers passed did activation occur. Fresh roster/session
  checks found 98/98 recorded player sessions on RCON3 and an empty, fresh roster
  on RCON4.
- Final public/API verification at **2026-10-06 18:20:27 UTC** confirmed active
  configuration, one report-worker owner per server, fresh rosters, all 92
  referenced frontend assets per server, HTTPS, CSRF and anonymous access denial.
- SMTP STARTTLS authentication still passes on both servers; no email was sent.
  Unrelated user configurations, original configuration-file hashes and
  protected container identities/running states were verified unchanged.
- Follow-up checks confirmed the routines were running, temporary deployment
  balance leases were released, and no new report-admin error markers appeared
  in the checked post-start logs.

No natural report-admin case had been recorded at final acceptance. These checks
prove deployment and runtime readiness, not a completed real-player kick or
full in-game end-to-end acceptance. See [feature documentation](../report-admin.md)
for the moderation and name-resolution limitations.
