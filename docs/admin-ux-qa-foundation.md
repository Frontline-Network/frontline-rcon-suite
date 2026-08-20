# Admin UX QA foundation

This milestone turns the admin interface's most important usability guarantees into repeatable checks. It does not replace the live product audit or manual game-server tests; it catches regressions before they reach those stages.

## Covered behavior

- Route smoke checks for the dashboard, live and team views, player records, map objectives, services, apps, and the Discord Report Bot.
- Responsive checks at 390 px, 768 px, and 1440 px, including horizontal overflow detection.
- Automated WCAG 2.0/2.1/2.2 axe scans. Serious and critical findings fail the test run; the complete axe result remains attached to the report.
- Keyboard checks for the main-content skip link, the `Ctrl+K` navigation shortcut, and the mobile navigation drawer.
- A 44 px minimum-target check for the important mobile navigation controls.
- HLL, HLL Vietnam, and multi-server context checks, including the API aliases `hllv`, `hll_vietnam`, and `vietnam`.
- Contract checks that distinguish a CRCON outage from a game-server outage.
- Explicit loading, online, offline, stale and unknown connection-state contracts, including cached-data timestamps.
- Dashboard regression checks that reject believable fallback values when live data is missing.
- German/English contract checks for the critical navigation, connection, error, and integration labels changed by this milestone.
- A limited-permission scenario proving protected player actions are unavailable to viewers and remain available to superusers.
- Runtime and console error collection during route checks.

The tests run against Mirage's deterministic fake mode. No production server, Discord integration, game server, credentials, or player data is contacted.

## Local commands

From `rcongui/`:

```bash
npm ci
npx playwright install chromium
npm test
REACT_APP_API_URL=https://rcon.example.org/api/ npm run build
npm run check:bundle
```

Useful focused commands:

```bash
npx playwright test e2e/route-smoke.spec.mjs
npx playwright test e2e/accessibility.spec.mjs
npx playwright test e2e/keyboard.spec.mjs
npx playwright test e2e/game-context.spec.mjs
```

The HTML report is written to `rcongui/playwright-report/`. Failed CI runs upload it for seven days.

## CI gate

The admin UI pull-request job now uses Node 22, installs Chromium, runs the Playwright suite, and only then builds the production bundle. A test or build failure blocks the pull request.

## Product changes introduced by this milestone

- A keyboard-visible “skip to main content” link.
- Explicit primary-navigation landmarks for desktop and mobile drawers.
- Translated accessible names and 44 px targets for the important navigation controls.
- Safe normalization of HLL Vietnam identifiers in the server selector.
- Fully translated connection explanations that do not assume the game is always HLL.
- Dashboard and header values now come only from confirmed API data; missing server, map, mode, player and image data is labelled unknown or unavailable.
- Cached data is retained after a failed refresh but clearly marked stale with its last successful timestamp.
- Dependent game-server polling stops while CRCON is unavailable, avoiding requests that cannot succeed.
- Permission-denied action menus now explain why no protected action is available; icon-only action buttons receive accessible names.
- Fake-mode switches for deterministic single-game, HLL Vietnam, unknown-game, and multi-server scenarios.

## Evidence limits and remaining work

- Automated axe checks find many common accessibility defects, but they do not prove full accessibility compliance. Screen-reader behavior, content clarity, focus order in complex dialogs, and destructive-action comprehension remain manual checks.
- The live `rcon3.fln.gg` audit still requires accepted screenshots at 390 px, 768 px, and 1440 px. Those screenshots must be captured from the signed-in live interface and inspected before they can be used as evidence.
- HLL and HLL Vietnam command compatibility still needs a real two-game-server matrix. Fake mode verifies UI context and routing, not RCON protocol behavior.
- Visual-regression baselines should be added only after the live audit establishes the intended reference states; otherwise tests would preserve accidental layout defects.

## Release policy

This milestone should remain a draft pull request until the automated checks are green and the live screenshot audit is attached. It must not be rolled out to production without explicit approval.
