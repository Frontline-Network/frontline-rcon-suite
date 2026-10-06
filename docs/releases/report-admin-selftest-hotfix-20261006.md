# Report-Admin: self-test exception and kick receipts — 2026-10-06

Deployed source: `8287643492cb1c95e8d839d570d66bf50359980b`, branch
`codex/report-admin-mvp`. Hotfix only: public version remains **v0.9.2**;
no GitHub release, tag or push was made.

## Scope and behavior

The user approved temporarily allowing self-reports for testing, then requested
private kick confirmations to reporters and an unmistakable Discord indication
of automatic action.

- RCON3 and RCON4 now have `allow_self_reports=true` with the existing active
  communication/teamkill rules. This is a **real-kick test exception**, not a
  dry run. It is default-off and server-local in the source configuration.
- Apps → Discord-Report-Bot → Report-Admin includes a DE/EN switch and warning.
  Disable **Allow self-reports for testing** and save when testing is finished.
  The separate leadership-vote self-report restriction is unchanged.
- Identity, live session, leadership role, same-team, freshness, Discord delivery,
  cooldown and the five-teamkills-in-five-minutes threshold remain enforced.
  Previously manual reports are never replayed when enabling the option.
- Only a durably confirmed kick sends the reporting player a private DE/EN
  receipt naming the kicked player. No success message for uncertain/failed
  kicks or dry runs. Self-reporters are skipped because they were kicked.
  Other offline/stale/changed-session recipients are also skipped. The receipt
  has a durable no-retry marker and does not create a warning against the reporter.
- Discord shows a green **Automatically kicked – player** card, a prominent
  automatic-action field with target/reason, and the report admin as handler.
  Closed cards have no sanction buttons. Non-success/manual states do not get
  this success marker. The displayed language follows Discord DE/EN settings.

## Deployment and backups

Private host state (contains credentials; never publish its contents):
`/root/hll_rcon_tool/.deploy-state/report-admin-selftest-20261006/`.

Fresh, fully readable custom-format PostgreSQL backups were made for both the
RCON installation and shared Discord service, along with configuration and
pre-change report-admin settings. RCON backup: 2,349,816,984 bytes,
SHA-256 `112724bf02c17a54270aca4dc0f67fc57a48ebd0ee70df4623ad5546fd73a9ce`.
Discord backup: 336,800 bytes. Previous images are retained under
`frontline/report-selftest-rollback-{backend,frontend,central}:20261006`.

Images retain all original base layers and carry the source commit label:

- Backend: `sha256:af4dd770becf20ed90d6056c1215e56d131837bb553d689a514577b927086d6e`
- Frontend: `sha256:ae48813fe9ca7596eec1d75a883d650619968837dc343867eb6ad77161f4e39b`
- Discord: `sha256:a0677ec66d88d880a9c3b7c1001c07b07dc304b7f29e099e87eeb80c4e2d30ac`

Only RCON3/4 backend, supervisor and frontend containers, the installation's
shared background/webhook consumers, and the shared Discord service were
updated. Other RCON containers retained their IDs and running states. No game
server, PostgreSQL or Redis restart and no schema migration. SMTP settings and
all runtime environment values were verified unchanged. The user's concurrently
selected RCON3 reason templates (30/6) were preserved.

Active Compose models: `hotfix.json` and `central-hotfix.json`; previous models:
`rollback.json` and `central-rollback.json` in the private directory. Use explicit
service names, `--no-deps --pull never`, and the existing project names. For a
rollback after activation, first stop new automated actions and safely cancel
pending reports, then restore/remove the new configuration key before starting
the older strict-schema backend. Merely setting it to false is insufficient for
the old schema, which rejects unknown keys. Do not restore a live database just
to roll back this source-only change or reactivate retired services.

## Verification

- 737 backend/API/leadership regression tests passed, plus two additional real
  HLL/HLLV message-wrapper tests confirming the receipt does not log a warning.
- 95 Discord service tests passed, including success titles, evidence, no action
  buttons and no false success indicators for other states.
- Production frontend build, 29 CSRF-client tests, 11 localization tests and
  English completeness checks passed.
- Network-isolated candidate imports and source checksums passed. The initial
  read-only image probe needed a writable temporary working directory for its
  startup log; corrected without relaxing network isolation or live mounts.
- RCON4 then RCON3 were updated under report/vote and balance execution guards.
  Both passed HTTPS, 92 referenced asset checksums each, authenticated config
  read/anonymous denial, CSRF, fresh rosters, one report-worker owner and running
  routines. No checked new report-admin runtime errors; guards were released.
- RCON4's self-report switch was already enabled concurrently through another
  configuration action when activation began. This was adopted without another
  configuration write. Only RCON3 still needed the switch enabled.

## Real pilot result

The user's new `!admin able redet nicht` report as **Biene** on RCON4 produced a
confirmed kick at **20:57:44 Europe/Berlin** (18:57:44 UTC). Incident
`dc64b2f4-f901-48cd-b9b2-aa8b73d5ac24` resolved with actor `system:report-admin`;
the success event was delivered. The three older manual self-reports stayed manual.

A read-only Discord GET of the existing message verified revision 3, title
**🤖 Automatisch gekickt – Biene**, first field
**✅ Automatischer Eingriff – Report-Admin**, green color and no action buttons.
The reporter notification was correctly recorded as skipped (`self_report`).
A separate reporter's private receipt has automated coverage but was not claimed
as a completed live test. No report, kick or test message was fabricated by the
deployment scripts.
