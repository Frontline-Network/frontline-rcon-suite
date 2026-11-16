# Frontline production deployments

Production must run from a clean checkout of the private Frontline repository.
Do not edit tracked files on the server. Runtime configuration belongs in the
ignored `.env`, generated `compose.yaml`, and ignored data directories.

## One-time GitHub access

Create a dedicated Ed25519 key on the server and register its public key as a
**read-only deploy key** on
`Frontline-Network/hll_rcon_tool-mobile-admin`. Configure an SSH host alias that
uses only that key, then add the repository as the `frontline` remote:

```sh
git remote add frontline \
  git@github-frontline-crcon:Frontline-Network/hll_rcon_tool-mobile-admin.git
git fetch frontline master
git switch --track -c master frontline/master
```

Keep the upstream CRCON repository as an `upstream` remote if it is needed for
future merges. Production deployments always come from `frontline/master`.

## Preflight and deploy

The deploy helper refuses a dirty checkout, a non-`master` branch, a
non-fast-forward update, or an invalid Compose model. The deployment creates a
PostgreSQL custom-format backup, tags the currently running images for rollback,
builds commit-addressed images, starts the stack, waits for health checks, and
prints the migration state.

```sh
./scripts/deploy_frontline.sh --check-only
./scripts/deploy_frontline.sh --deploy
```

The deployed commit tag is stored as `CRCON_IMAGE_TAG` in the ignored `.env`.
Backups and deployment metadata are written below `.deploy-backups/` and
`.deploy-state/` with owner-only permissions.

The Frontline override enables the HTTP and WebSocket readiness probe for managed
backends 1–4, including when an older generated Compose file disabled its health
check. The deployment helper additionally generates the same override for every
configured backend up to number 32, without creating unconfigured services. The
helper checks that each target backend image contains the probe and health endpoint
before stopping workers; an incompatible image stops the deployment for review. The
check reflects readiness; it does not prevent a brief interruption while a backend
container is replaced. A deployment started by an older helper can update backends
1–4 immediately; additional instances receive this override on a later deployment
run by the updated helper, or when their generated Compose file is updated.

## Preserve password recovery on every rollout

SMTP credentials belong only in the installation's ignored `.env` (owner-only
permissions), never in Git, release notes, image layers, or command output.
Back up this file before changing it and preserve it when updating or regenerating
Compose. Do not replace it with `default.env`.

Multi-server installations support `CRCON_PASSWORD_RESET_ENABLED_<n>` and
`CRCON_PUBLIC_URL_<n>` for instances 1–10. An unset or empty override falls back
to the unsuffixed value. Give each enabled instance its **own public HTTPS origin**
so reset links return to the correct server. Keep the global enable flag `false`
when shared workers have no public origin. Existing single-server configurations
using the unsuffixed values continue to work.

For Frontline installations, retain the SMTP settings on every authorized rollout.
The instance-specific flags/origins below apply to RCON3/4; other deployment targets
need their own verified origins and are not activated by this example:

```dotenv
EMAIL_HOST=mail.fln.gg
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@fln.gg
DEFAULT_FROM_EMAIL=noreply@fln.gg
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
CRCON_PASSWORD_RESET_ENABLED=false
CRCON_PASSWORD_RESET_ENABLED_3=true
CRCON_PUBLIC_URL_3=https://rcon3.fln.gg
CRCON_PASSWORD_RESET_ENABLED_4=true
CRCON_PUBLIC_URL_4=https://rcon4.fln.gg
```

Preserve the separately stored `EMAIL_HOST_PASSWORD`; it is intentionally absent
from this example. Do not activate retired instances 1/2.

For pinned-image deployments, derive each service from its actual running
container's `com.docker.compose.project.config_files`, not an older release's
snapshot. The RCON3/4 configuration-only activation on 2026-10-04 is recorded in
`.deploy-state/password-recovery-20261004/`. When regenerating from an older
template, append its private `compose.smtp-overlay.json` last. This overlay
requires the private variables and can also be used with newer templates.
The host's `.deploy-state/SMTP-ROLLOUT.md` contains the configuration rollback
instructions. Never print resolved Compose files: they contain credentials.

Before rollout, validate the Compose model without printing it. Afterwards,
verify the actual Django SMTP configuration, TLS/authentication, the per-instance
public origin, and `GET /accounts/password_reset/` with `Accept: application/json`
(`available: true`). Do not log the returned CSRF token. SMTP authentication alone
does not prove mailbox delivery; only send a test email to an agreed recipient.
Users also need a reachable email address on their account in Administration.
Do not invent or overwrite account addresses during deployment.

## Rollback

Do not automatically downgrade database migrations. If application health fails,
use the previous commit and the `rollback-<sha>` images recorded in the newest
`.deploy-state/*.env` file. Restore its PostgreSQL backup only when the failed
release changed data incompatibly, and verify the restore in a separate database
first.

After resolving the cause in GitHub, return the production checkout to
`frontline/master` and use the normal preflight/deploy commands again.
