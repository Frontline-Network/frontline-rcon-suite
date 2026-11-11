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

## Form usability revision

- Rule details appear only while that rule is enabled; toggling retains values.
- Added plain-language explanations for goals, qualification and shared limits.
- Events and weapon challenges reveal their details after activation.
- Searchable multiple weapon selection uses the active game profile catalogue.
  A dedicated read endpoint uses the existing Seed-VIP read permission, without
  requiring Seeding-Automod permissions. Existing unknown selections are kept.
- Disabled challenge drafts may have no weapons; active ones require a selection
  in both frontend and backend validation.
- Rewards use the configured autobalancer volunteer command (normally !balance),
  not a separate !balancevip command. An internal switch path distinguishes
  registered volunteers from forced switches; observed switch/stay and seeding
  safeguards remain required for rewards. This path is not exposed as an API action.
- Validation: 123 backend tests (VIP rewards, autobalancer service and volunteer
  flow), 3 browser tests and production build passed. Build still reports the
  existing bundle-size advisory. No live deployment or game-server testing.
