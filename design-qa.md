# Kartenabstimmung – Design QA

## Vergleichsgrundlage

- Source visual truth: `C:\Users\chris\.codex\generated_images\01a0052a-7e8d-7411-8b78-1a415453783b\exec-a864bbd0-2ee9-4c3d-b95a-582b53f66ce0.png`
- Implementation: `http://127.0.0.1:3003/settings/maps/votemap/whitelist`
- Final implementation screenshot: `C:\Users\chris\AppData\Local\Temp\votemap-pool-final-3.png`
- Full-view comparison evidence: `C:\Users\chris\AppData\Local\Temp\votemap-pool-final-comparison.png`
- Source pixels: 1487 × 1058 px.
- Final implementation pixels: 2353 × 1272 px at device scale factor 1.
- Normalized comparison: the source and the earlier 1280 × 720 implementation capture were both normalized to 1280 px width before the combined comparison was judged. The latest screenshot confirms the same post-fix layout at the larger desktop viewport.
- State: dark theme, German locale, authenticated fake/demo server, Kartenpool tab, clean/saved draft with two selected maps.

## Findings

No actionable P0, P1, or P2 visual differences remain.

- Typography: the established Frontline display and UI type hierarchy is preserved. Headings, labels, helper copy, and compact metadata retain the product's weight and density rather than copying the mock literally.
- Spacing and layout: the workbench follows the selected two-column composition, angular borders, compact rows, clear section rhythm, and a persistent action area. The responsive version collapses to a single-column map view and uses a two-row mobile action grid.
- Colors and tokens: existing theme tokens drive surfaces, borders, muted text, warning states, success states, and action colors. No detached mock-only palette was introduced.
- Image quality: real map-layer assets are used with consistent crops and no placeholder or hand-drawn replacements.
- Copy and content: all new operator-facing copy is localized in German and English. Internal map IDs are hidden during normal use but remain visible and removable when a stale server entry requires operator action.

## Focused-region comparison

A separate crop was not required: the combined comparison keeps the complete map-pool workbench readable, including both panels, map thumbnails, filters, row actions, and the action bar. The live-vote and settings tabs were additionally inspected directly in the browser for information hierarchy and control alignment.

## Comparison history

1. Initial comparison found P1/P2 issues in the live-vote summary, zero-vote leader treatment, mobile vote-row tracks, action-panel order, pool synchronization, and the mobile action bar.
2. Fixes applied: responsive summary grid, explicit mobile tracks, current-vote-first DOM order, guarded server/draft synchronization, set-based whitelist comparison, safe sticky offsets, and zero-vote rows without a leading state.
3. Follow-up comparison found remaining contract and usability gaps around mixed external config changes, numeric bounds, concurrent pool mutations, and empty-pool submission.
4. Fixes applied: hidden `enabled` state is merged independently, numeric limits now match the backend contract, save/reset mutations are mutually locked, an empty pool is explained and cannot be saved, tabs are filtered by view permission, and the workbench entry redirects to the first permitted tab without requiring the map-catalog permission for status or settings.
5. Post-fix evidence: `C:\Users\chris\AppData\Local\Temp\votemap-pool-final-3.png`; browser checks confirmed clean and dirty pool states, add/remove/reset, empty-pool validation, destructive confirmation, stable manual number entry, invalid-number save blocking, and reset restoration.

## Runtime and interaction checks

- Primary interactions tested: tab navigation, map add/remove, draft reset, empty-pool guard, destructive reset confirmation, number-field blank/intermediate typing, numeric validation, and configuration reset.
- Browser logs checked: no runtime errors; only the existing React Router future-flag warning and normal Vite/Mirage development logs were present.
- Build: Vite production build passed with the existing chunk-size warning.
- Contract checks: config compatibility, polling budget, and admin-action contract passed.

## Follow-up polish

- P3: the demo catalog intentionally contains only a few maps, so production density with the full HLL/Vietnam catalog should be sampled after rollout.
- P3: source and implementation use different full-page aspect ratios because the implementation remains inside the existing application shell; the normalized workbench comparison accounts for that intentional constraint.

final result: passed
