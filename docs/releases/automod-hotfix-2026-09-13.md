# Automod hotfix – 2026-09-13

- Seeding: known player positions enforce the protected combat-area boundary
  for both teams, irrespective of who holds the middle objective. Capturing or
  losing the middle no longer clears an ongoing positional warning sequence.
- Keep the score guard for the offense-points fallback: offense points earned
  while contesting the permitted middle are not proof of a boundary crossing.
- Level automod: when kicks are disabled and punishments are enabled, continue
  punishing an ongoing role-level violation at the configured interval instead
  of stopping permanently after the finite punishment limit. The finite state
  window remains bounded. Zero still disables punishments; kick-enabled
  escalation and the level-one exception are unchanged.
- Regression coverage includes HLL (Carentan), HLLV (Van Tuong), both teams,
  ownership changes, warnings, grace periods, safe fallback behavior, disabled
  seeding rules, population limits, and non-Warfare modes. Role-level tests cover
  the HLL `officer` and HLLV `squadleader` alias, finite/unlimited punishment
  settings, and kicks both enabled and disabled.

Publication: merge into the main branch and publish the next official patch
release, v0.8.4, with backend/frontend images for amd64 and arm64. The operator
requested an official release after the initial narrow hotfix plan; the narrow
v0.8.2-derived image was not deployed.

Deployment scope: HLL1 only, using the official release images. Upgrading from
v0.8.2 also includes the v0.8.3 changes and its merged Django migration. Restore
the fresh backup into an isolated database and rehearse migrations before
updating production. Preserve automod settings, permissions, the pre-v0.8.2
backups, and the original runtime configuration. Do not restore the production
database automatically. No rollout to other RCONs is included.
