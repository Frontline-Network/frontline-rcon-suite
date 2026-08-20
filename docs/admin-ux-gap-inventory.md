# Administrator UX gap inventory

Status: code-based inventory on 2026-08-20. This is not the live visual audit.
The required RCON3 screenshots at 390, 768, and 1440 px remain an explicit gate
because the in-app browser connection could not be established.

## Evidence inspected

- route and task navigation definitions;
- dashboard composition and live-state components;
- generic and destructive player-action dialogs;
- general, schema-driven, Auto Settings, map, and service settings;
- Autobalancer and the four legacy Automods;
- Discord Report Bot setup and translations;
- HLL/HLLV identity contracts and map APIs;
- current route, permission, keyboard, touch, translation, API, game-context,
  admin-action, and axe tests;
- bundle budget and performance documentation.

## What is already strong

1. Global state no longer needs to guess a server, game, map, or connection
   state. CRCON and game-server health are separate, and unknown, stale,
   partial, disabled, and offline states exist.
2. Task-oriented navigation and permission-aware destinations are implemented
   without changing stable routes. A user can discover a protected route and
   see why it is unavailable.
3. Squad dissolution is the current reference implementation for a destructive
   action: current server/game context, reason, review, second confirmation,
   per-target outcomes, retry-failed-only, and an audit link.
4. General server settings have a first effect summary with server value,
   draft, recommendation, conflict hint, read timestamp, permission reason, and
   draft reset.
5. The Autobalancer already explains disabled, shadow, manual, and automatic
   modes and exposes decisions and history. It is the correct explanation
   benchmark for other Automods.
6. Route-level code splitting and a checked initial-bundle budget now protect
   loading performance. See `docs/performance-scaling.md`.
7. Auto Settings now have a pure preview API contract that can explain rule
   priority, effective commands, missing scenario values, duplicate maps,
   unavailable game-profile maps, and overlaps without sending RCON commands.
8. Resource telemetry now has a bounded, container-aware API contract with
   measurement timestamps, data age, history, source, warnings, and a client
   polling cadence. The operations-first dashboard presentation is still open.
9. `get_status` now exposes the active game, profile-backed game modes, and
   protocol-backed timer capabilities. Users without the separate
   connection-info permission still receive a truthful HLL/HLLV context, and
   HLLV no longer receives the invalid Skirmish timer controls. Remaining
   features still need the same capability treatment and visible labels.
10. `get_general_setting_effects` now supplies a versioned, permission-aware
    state matrix for the nine direct game-server settings. It preserves partial
    results, separates recommended values from unknown protocol defaults,
    reports Auto Settings candidates without claiming an active rule, and
    distinguishes failed audit attempts from successful changes. The existing
    cards do not consume this contract yet.

## Prioritized gap matrix

| Priority | Surface | Code evidence | User risk | Required product outcome | Proof required |
| --- | --- | --- | --- | --- | --- |
| P0 | Generic player actions | `ActionDialog.jsx` and `ActionForm.jsx` use one generic confirmation; only squad dissolution uses the full safe flow | Kick, punish, ban, blacklist, message, or bulk action can be confirmed without a complete server/game/effect review; failed targets cannot be retried selectively and no audit link is offered | Move critical and bulk actions onto a shared prepared-action contract with target, server, game, reason, duration, message, scope, reversibility, result per target, retry failed, and audit link | HLL/HLLV, bulk partial-failure, permission, stale/offline, keyboard, 390 px, and audit-link tests |
| P0 | Auto Settings | `settings/autosettings/index.jsx` is a Monaco JSON editor; the preview contract is not yet visible | Rule order, defaults, overlaps, duplicate maps, and effective values remain hard to understand | Basic rule builder as default, Advanced JSON retained, explicit simulation context, priority and effective-value preview, conflict resolution, and map-profile validation | Current RCON3 screenshots, DE/EN, HLL/HLLV maps, invalid JSON, overlap, duplicate, no-data, keyboard, axe, and responsive tests |
| P0 | Generic settings | A shared setting-effect API now covers the nine direct game-server settings, but schema pages still call their modes Visual/Code and the cards do not consume configured/effective/default/recommended/side-effect/restart/audit metadata | A saved value can be mistaken for the value currently enforced by the game server or automation | Connect the contract to shared setting summaries, then extend it to schema settings with Basic/Advanced modes | Current screenshots plus HLL/HLLV, permission, stale/offline, reset, audit, translation, keyboard and responsive tests |
| P0 | Discord diagnostics | The card supports pairing, guild/channel/roles, provider/model, enable, save, and test; it has no explicit callback/broker health, last successful delivery, repair action, or expandable technical details | Administrators see generic errors and cannot locate whether CRCON, callback, broker, Discord, or AI caused the failure | Seven-step setup assistant and operational health panel with component states, timestamps, test outcome, repair action, provider/model/cost, and safe technical details | Pairing, wrong host, callback, broker, Discord rate-limit, AI unavailable, reconnect, multiserver, and two-Guild tests |
| P1 | Legacy Automods | Level, No Leader, Seeding, and No Solo Tank use the generic schema form and long English code notes; only Autobalancer exposes mode/decision history | Administrators cannot consistently tell what will happen, what last happened, or how to test safely | Unified Off / Observe / Manual / Automatic model where supported, last run, decision, reason, affected players, preview, and guardrails | Status API contracts, decision fixtures, DE/EN, HLL/HLLV role compatibility, and no-action shadow tests |
| P1 | Dashboard hierarchy | `dashboard.jsx` renders the large Frontline App promotion before settings, Automods, services, maps, moderation, and logs | Operational problems can be pushed below promotional content | Incidents, CRCON/game-server health, moderation, automation, map status, and resources first; promotion after operating state | Live screenshots at all target widths, offline/stale/partial fixtures, task-step comparison |
| P1 | Resource visibility | `get_system_usage` now returns a cached, container-aware v2 contract and the sidebar respects its polling cadence; the dashboard still lacks a resource history and operational explanation | Capacity and runaway-process problems remain hard to investigate from the main operating view | Present used/total CPU and RAM, time range, samples, data timestamp, source, thresholds, and explainable warnings on the dashboard; preserve unknown values when unavailable | Live container sampling, stale/partial states, responsive chart tests, and current screenshots |
| P1 | Translation quality | Autobalancer help, dashboards, round history, and parts of config mode labels contain extensive hard-coded German strings | English UI becomes mixed-language and new copy is outside translation checks | Move changed operator-facing strings into locale resources and extend the translation contract beyond a hand-picked key list | Hard-coded-string check plus DE/EN route render tests |
| P1 | Accessibility coverage | axe covers four routes at three widths; keyboard tests focus on shell navigation; touch-target coverage focuses on important navigation controls | Critical dialogs, settings, Automods, and Discord can regress unnoticed | Extend axe, keyboard, focus-return, announcement, zoom/reflow, and touch-target tests to every changed critical flow | No serious/critical axe results, documented manual 200% zoom and screen-reader spot checks |
| P1 | HLL/HLLV coverage | Status identity and supported modes now come from the active profile; timer controls additionally use protocol-backed capabilities, and selected action/context tests exist; broad settings/Automod/map-action matrices do not | A feature may silently work for only one protocol/profile | Extend the timer pattern to remaining feature capabilities, add visible compatibility labels, and pair E2E fixtures for both games | HLL and HLLV fixtures for every changed command and setting; unknown future profile remains unknown |
| P2 | Component documentation | No Storybook or comparable component catalogue was found | Status, setting, confirmation, empty, and error patterns can drift between pages | Lightweight component states catalogue using real components and fixtures, not a second design system | Documented states for connection, setting effect, destructive review/result, diagnostics, and empty/error/loading |
| P2 | Polling and request budgets | Dashboard requests up to 100 games and broad log groups; no request-count or polling regression budget was found | More instances can amplify avoidable backend, CPU, RAM, and network load | Per-route request budget, shared cache policy, bounded payloads, and explicit refresh cadence | Request-count snapshots, payload sizes, cache hit evidence, and before/after CPU/RAM sampling |

## Structural versus visual work

The following work is safe to continue without inventing a visual direction:

- API contracts for prepared actions, remaining effective settings, Automod decisions,
  Discord health, and resources;
- deterministic fake fixtures for offline, stale, partial, permission, HLL,
  HLLV, and multiserver states;
- translation and hard-coded-string contracts;
- polling/request budgets and backend tests;
- component-state data contracts.

The following work must wait for current screenshots from the chosen browser:

- dashboard reordering and density changes;
- Auto Settings Basic editor layout;
- Discord setup-assistant layout;
- component styling, responsive spacing, and visual regression baselines.

## Recommended milestone order

1. Finish the RCON3 visual audit and record task-step baselines.
2. Generalize the safe squad-dissolution pattern into a prepared-action
   contract, starting with kick/punish and then ban/blacklist/bulk actions.
3. Connect the Auto Settings preview contract to a Basic editor, using the
   existing map-profile API and keeping Advanced JSON.
4. Add effective-setting metadata and audit provenance at API level, then apply
   the shared setting summary across schema-driven pages.
5. Add Discord component-health diagnostics before reshaping setup into a
   seven-step assistant.
6. Standardize legacy Automods using Autobalancer's explanation model.
7. Present the resource telemetry contract and reorder the dashboard around
   incidents and operating health.
8. Finish component documentation, broad accessibility coverage, HLL/HLLV
   matrices, polling budgets, visual regressions, merge gates, and release.

## Completion boundary

This inventory does not prove the product objective complete. It identifies
current code evidence and the evidence still needed. No visible redesign,
merge, release, or production rollout is authorized by this document.
