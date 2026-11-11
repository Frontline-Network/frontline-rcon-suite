# Local next-release integration trial — 2026-11-11

Base: 47801cfe, branch codex/next-release-local-integration-20261111.
Imported the additional VIP rewards feature from the uncommitted work in
CRCON APP Frontline (base 5fbb9865). Unrelated mobile and level changes excluded.
Historical source staging results are in vip-rewards-staging.md; those results
are not acceptance evidence for this combined candidate.

## Local form trial

Run the frontend in Mirage fake mode. Current local preview:
http://127.0.0.1:3062/settings/others/vip-rewards

Saving only changes Mirage memory. Reload resets it. No live server, player
messages or VIP grants are involved. The visible banner explains this.
The fake validation endpoint accepts configurations; this demo does not prove
real backend validation or database persistence.

## Validation

- 60 tests passed: test_vip_rewards.py, test_broadcast_activity.py,
  test_broadcast_campaigns.py.
- 2 Playwright tests passed: save/discard, no external HTTP requests,
  mobile viewport without horizontal page overflow.
- Production frontend build passed before the final navigation label additions.
- git diff --check passed.
- Registered hooks with the current lazy loader and included the worker in both
  supervisor layouts. New migration follows the existing mobile-context head.

## Before release

- Review the long form with the user; simplify explanations and progressively
  disclose rule details as appropriate.
- Complete English localization of the imported form.
- Validate the combined migrations on a restored, isolated test database and
  run the full combined worker/integration acceptance suite.
- Review failure handling of shared VIP locks and forced-switch tracking.
- No release, rollout or live feature activation was performed in this task.
