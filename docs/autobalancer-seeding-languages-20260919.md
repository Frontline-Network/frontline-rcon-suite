# Autobalancer follow-up — 19 September 2026

## Production diagnosis (read-only, 08:34 UTC)

Since the preceding hotfix (18 September, 18:03 UTC), RCON3 recorded four
automatic candidates and RCON4 two. All six were aborted; none had a recorded
confirmed execution. Three ended because counts were already balanced, two on
inconsistent counts and one because the candidate entered a more protected
squad. These are distinct from successful switches; no test switch was sent.

The servers use auto mode, 45 seconds stable difference, 30 seconds for
volunteers and a 180-second candidate deadline. Difference <= 2 is acceptable.
The main automatic flow balances player counts, not strength alone. Selected
players are switched only after a fresh death. Exact independent count agreement,
Commander/squad protection and connection/cooldown guards remain mandatory.

Both servers started balancing at 40 players, while their enabled cap-fight
seeding rule ends at 50 players. There was no explicit seeding integration.

## Changes

- Seeding is an unconditional automatic safety gate. While enabled, the largest
  configured, enabled seeding rule's upper population limit takes precedence over
  the balancer minimum. Empty role/weapon rules do not contribute their default
  100-player limits. Protection also applies below enforcement minima. At the
  upper threshold seeding ends, matching the automod's `< max_players` boundary.
  Disabling seeding enforcement removes this specific gate; the balancer's own
  minimum remains. The game's native balancer and explicit manual admin moves
  are not modified.
- Unknown seeding configuration blocks safely. Every production snapshot reads
  it, and execution rechecks it under the existing execution lock. Active calls
  are cancelled/disarmed; `!balance` explains the pause. Leaving seeding begins
  a fresh observation, never resumes an old candidate.
- Already selected candidates tolerate a cumulative maximum 15 seconds of
  count-only data jitter. During this pause they are disarmed and cannot switch.
  Recovery revalidates the candidate and requires a new death after recovery.
  Old/delayed/future/non-finite deaths cannot trigger a switch. The candidate's
  original deadline is not extended. Other safety blocks cancel normally.
- `message_language` selects `de`, `en` or `de+en`. Existing configs default to
  German, preserving `messages`; editable `messages_en` is a separate English
  pack. Both languages mean separate private messages, German first. Includes
  invitations, selections, outcomes, command replies, unavailability and manual
  squad-action feedback. Both language sends are attempted independently, with
  no automatic delivery retry. Custom command and placeholder validation remain.
- The normal auto/manual dashboard no longer advertises historical unreviewed
  proposals as open tasks or pilot prerequisites. Review/pilot tools are limited
  to explicit shadow mode. Current candidate comes only from current status,
  never the historical queue. Last intervention means a confirmed execution in
  the loaded history, not an accepted review. History remains available for audit.
- Fixed schema form change echoes which could reset fast selections. Memoized
  UI schema and no-op equality guard prevent feeding identical cloned data back.
  Referenced message-pack fields also use UI-language labels.

The frontend live-balance assistant uses live scores. The automatic backend
still combines live observations with available performance history; this task
does not silently change that selection strategy or delete audit history.

No migration, release, production configuration write or rollout in this task.
Dual-language sending must be explicitly selected when deploying/configuring.

## Validation

- 1,186 backend tests passed: autobalancer, seeding/geofences/map sides,
  leadership votes and HLL/HLLV game profiles (65 existing warnings).
- 12 repeated browser checks passed for both message-pack languages, normal
  auto/manual dashboards and the retained shadow review/history workflow.
- 16 browser checks passed for the final Autobalancer changes and shared
  configuration forms, including narrow viewports and nested-field edits.
- 11 localization unit tests, the 5,193-key DE/EN catalog contract,
  configuration compatibility and workbench contracts passed.
- Production frontend build passed; existing large-chunk warnings remain.

These are isolated/local checks, not proof of a successful production switch
with this new code. No live player was messaged, moved or kicked for testing.
