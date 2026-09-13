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

HLL1 deployment scope: a commit-addressed supervisor hotfix image derived from
the installed v0.8.2 image, replacing only the two automod modules. No frontend,
database migration, settings change, or rollout to other RCONs is included.
The public frontend version therefore remains v0.8.2. The effective hotfix
revision is recorded in the supervisor image labels and private deployment
manifest. Preserve the tested pre-v0.8.2 backups and create a fresh rollback
backup before deploying. Do not restore the production database automatically.
