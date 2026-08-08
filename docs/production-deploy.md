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

## Rollback

Do not automatically downgrade database migrations. If application health fails,
use the previous commit and the `rollback-<sha>` images recorded in the newest
`.deploy-state/*.env` file. Restore its PostgreSQL backup only when the failed
release changed data incompatibly, and verify the restore in a separate database
first.

After resolving the cause in GitHub, return the production checkout to
`frontline/master` and use the normal preflight/deploy commands again.
