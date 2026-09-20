# Autobalancer notification/count hotfix

RCON3 investigation on 2026-09-18 found 47 invitations followed by 47 cancellation
popups around 17:24–17:25 UTC, with no `!balance` command in that interval. The
cancelled decision had not sent a team switch. Every invitee was incorrectly
treated as somebody whose registration needed cancellation.

## Changes

- Cancellation feedback goes only to accepted/pending volunteers and an already
  announced automatic candidate, never merely to invitation recipients.
- Feedback is short and bilingual. Internal abort details remain in the admin
  decision audit and application log. Uncertain/already-sent switches ask for
  admin review instead of falsely promising that the player's team is unchanged.
- An atomic Redis reservation limits invitation attempts to one per player and
  server every 300 seconds, even after a failed/uncertain send, map change or
  worker restart. This does not suppress explicit command replies or important
  selection/completion notices. There is no configuration migration.
- Candidates, roles, squads and counts now come from the same timestamped bulk
  roster, not the UI roster's intersection with a separately cached ID list.
  Live profiles enrich this list but cannot remove a connected player. Missing
  profile data means zero known connection time, not assumed eligibility.
- Independent game-state team counts must still match exactly. One bounded
  refresh of the exact cached game-state/bulk keys is allowed; persistent
  inconsistencies still block balancing. No extra RCON action retry is added.
- Duplicate IDs, invalid rows/roles or stale/future samples fail closed. A sample
  which ages beyond ten seconds during enrichment is also unusable for balancing.

Existing protection tiers, native balancing, the death-trigger requirement,
manual approvals, map guards and uncertain-switch handling remain unchanged.
No production messages, votes, deaths or team switches are fabricated for tests.
