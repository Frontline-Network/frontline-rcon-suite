# Password recovery activation — 2026-10-04

Configuration-only change on `rcon3.fln.gg` and `rcon4.fln.gg`.
Both still run the unmodified v0.9.1 release images. The separately committed
feature-announcement carryover was **not** deployed. No GitHub release was made.

## Configuration and preservation

- SMTP: `mail.fln.gg:587`, certificate-verified STARTTLS.
- Authentication account and sender: `noreply@fln.gg`.
- Password stored only in private runtime configuration, never in this repository.
- Reset links use each instance's public HTTPS origin.
- Global activation remains off; instance overrides enable only RCON3/4.
- Preserve these settings on future deployments as described in
  [the deployment guide](production-deploy.md#preserve-password-recovery-on-every-rollout).

Private configuration backup and rollback models:
`/root/hll_rcon_tool/.deploy-state/password-recovery-20261004/`.
The earlier verified full v0.9.1 database backup remains intact. No database
migration or account modification was needed. Configuration files use mode 0600,
and the private backup directory uses mode 0700.

Only `backend_4` and then `backend_3` were recreated, using the same image IDs.
Vote/balance execution guards covered the replacements. All other containers,
including the game-facing supervisors, central Discord service, database and
Redis, retained their identities and running states. RCON1/2 remain stopped.

## Verification

- Both backends healthy, unchanged v0.9.1 image IDs and unrelated environment.
- Django SMTP connections authenticate successfully with TLS; no email sent.
- Public JSON reset endpoints return HTTP 200, `available: true` and a CSRF token.
- Public version endpoints still report v0.9.1.
- Account/password/email fields, permission grants and all user configuration
  remained unchanged.
- Private `.env` plus the required-variable SMTP overlay reproduce the intended
  Compose model; resolved-model comparison passes without printing secrets.
- Five template regression tests pass. Docker Compose interpolation checks pass
  for disabled defaults, legacy global fallback, per-instance origins and explicit
  disabling (ten instances each).

Two initial RCON4 verification attempts rolled back safely: the first probe used
the wrong Python import path; the second encountered a transient HTTP 502 during
Docker DNS refresh. The probe now uses the application directory and bounded
retries for network errors. Subsequent activation and final checks passed.

## Remaining delivery prerequisite

Initial inspection found 22 active accounts with usable local passwords, all
without an email address. A later read-only check after activation found 21 still
missing an address. This deployment did not modify any account addresses.
Administrators must add each user's own reachable address in Administration.
Mailbox delivery has not been tested; send a test only to an agreed recipient.
