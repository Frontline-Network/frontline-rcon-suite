# French localization review status

This is a working record, not approval to deploy. Counts below refer to the English main and lazy settings catalogs (4,945 main strings and 452 lazily loaded settings-panel strings at the time of review). Catalog growth can change these counts; parity checks use the current English modules.

## Reviewed main-catalog areas

- Guided configuration forms: 1,180 strings compared against English, including the separately reviewed autobalancer configuration overlay. This includes VAC and teamkill bans, player-name checks, RCON, log retrieval, sanctions and seeding rewards. Most drafts began as machine translations; 357 form entries received explicit corrections in `repair-french-configforms.mjs`, in addition to the targeted automatic-sanction corrections.
- Settings: integrations 129, general server settings 44, server name/SFTP 21, console administrators 74, mobile 46 and Discord reports 140. Player safety, privileges, confirmation and failure behavior were prioritized.
- Records: player records 53, blacklist records 105, player profiles 44, VIP records 91, audit logs 105 and game logs 93. Player drawer/editor add 84 strings.
- Live operation: player/team/table views 298, live balance 111, dashboard 189, statistics 297, shared operations 48 and operator messages 161. These were compared against English; numerous safety and status errors were corrected.
- Reviewed overlays from parallel work: `fr-core.js` (authentication, errors, connection status and mobile navigation), `fr-common.js`, `fr-actions.js`, `fr-incidents.js`, `fr-autobalancer.js`, `fr-campaigns.js`, `fr-navigation.js` (navigation and sidebar), `fr-maps.js` and `fr-account-interface.js` (appearance, theme, selection, table configuration, passwords, language and updates). `fr.js` composes these over the remaining draft catalog.
- Other reviewed namespaces: live log feed, brand, player identity, shared fields, match status, apps, setting effects, server settings, authentication, about and API documentation: 187 strings.

## Lazy settings panels

All 415 autobalancer-panel texts and 37 texts in the game, controls, camera and mobile panels were compared against the English source. Particular attention was paid to test mode, manual approval, incomplete live data, historical reconstruction, timed actions and current versus historical results. The reviewed texts remain in `fr-settings-panels-draft.json`.

## Outstanding work and limitations

- The 358 remaining main-catalog texts in `settings.{profanity,templates,autosettings,welcome,others,generalTabs,game,adminCam,desktopMobile,broadcast,config,services}` were compared separately by a parallel agent and are composed via `fr-settings-remaining.js` and `fr-settings-others.js`. Independent release checks remain outstanding.
- The generated draft was originally machine translated and contained serious errors, including reversed implications and damaged technical tokens. A pass against the English source reduces these risks but does not constitute independent native-speaker or domain-expert approval.
- Text entered by customers or returned by external services is not translated automatically. Server-side messages in other automods need separate language behavior; this UI review does not make those customer-configured messages trilingual.
- Strings outside the catalogs, server-rendered views, embedded admin, operator messages and runtime language branches need their own integration review. Console delivery and readability require an actual console test.
- Rebuild and test the effective composite locale, including lazy panels and reviewed overlays. Do not rely on prior staging artifacts, which predate later edits. Run meaningful browser and production-readiness checks before any installation.

## Checks

- `node --test src/i18n/french-catalog-draft.test.mjs` checks English key coverage, nonempty text, `{{…}}`, `{…}` and `<VARIABLE>` markers.
- `node --test src/i18n/fr-balance.test.mjs src/i18n/fr-settings-safety.test.mjs` checks selected consequential meanings, including inactive/test mode, incomplete data, irreversible actions, and game-admin behavior.
- Separate overlay tests cover French actions, autobalancer forms, core UI, campaigns, navigation/maps and account-interface copy. Key/placeholder parity cannot establish semantic correctness.
- `node scripts/audit-french-draft.mjs` detects a limited list of known machine-translation errors. A clean result is not a general quality guarantee; retain the original reports for traceability.
