# English interface completeness audit

## Scope and method

The audit covers the administration UI and the public statistics UI. Parallel
reviews covered (1) live views and statistics, (2) settings and integrations, and
(3) shared components, records, dates and error handling. A separate review
checked the combined implementation for behavior regressions.

The existing central DE/EN catalogs already had matching keys. Most defects were
German text rendered outside those catalogs, German system messages returned by
the backend, or memoized/date-library values that did not follow a language change.

The automated contract currently examines 560 production source modules, 5,184
catalog keys (including lazy settings), nine local bilingual objects and 4,117 static translation
references. It also checks English coverage of the public UI's German base keys.
These counts describe checked structure, not a claim that static analysis proves
every possible runtime string or every language is complete.

## Repairs

- Extracted the live balance assistant and six Autobalancer settings panels into
  matching English/German catalogs, including dialogs and accessible labels.
- Translated game/weather controls, admin camera, common save/state controls,
  legacy VIP screens and known leadership-vote results.
- Added an exact system-message registry for backend balance and live-map text.
  Recognized templates preserve player names, squad names and diagnostic details.
  The registry is used at display boundaries; business comparisons and submitted
  payloads retain their original values.
- Corrected date-picker localization, memoized labels, dates, numbers, initial
  document language and an existing hour/minute formatting typo.
- Added `check:i18n` to the GitHub quality workflow. It checks catalog parity,
  empty values, interpolation parameters, duplicate catalog properties, static
  references, local bilingual dictionaries and selected hardcoded JSX regressions.
- Made the existing history-workbench source contract tolerate Windows line endings.
- Register the extensive settings translations synchronously with their lazy
  route components. The initial production bundle remains within its existing
  size limits; no budget increase was needed.

## Verification

`npm run check:i18n` runs the structural audit and 11 dedicated Node regressions.
Additional English browser tests cover live balance review, compact mobile
layout, settings/history, the Discord setup flow and leadership outcomes, records,
live-map hints and language changes through the actual language menu. The normal
German browser suite remains part of the release gate, alongside action safety,
configuration compatibility, builds and bundle-size limits.

Browser tests use synthetic local data. They do not perform actions on production
players or establish real-game moderation outcomes. CI also runs the unchanged
backend and Discord-service suites before release approval.

## Intentional limits

Player chat, configured server messages, names, admin comments, allegations and
unknown backend details are never heuristically translated. Existing bilingual
player-facing messages and input aliases remain intact. English is not silently
enabled for accounts that selected German. This work does not change voting,
Seeding, balancing or punishment policy and introduces no database migration.
