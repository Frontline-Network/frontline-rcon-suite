# Design QA — Live-Spiel / Option 2

## Evidence

- Source visual truth: `C:\Users\chris\.codex\generated_images\01a0052a-7e8d-7411-8b78-1a415453783b\exec-1da4afa6-0f8a-48d1-a98d-1440a8f4302d.png`
- Browser-rendered implementation: `C:\Users\chris\OneDrive\Dokumente\Autobalancer\hll_rcon_tool-steam-enrichment\.tmp\product-design\live-game-option2-qa.png`
- Normalized implementation: `C:\Users\chris\OneDrive\Dokumente\Autobalancer\hll_rcon_tool-steam-enrichment\.tmp\product-design\live-game-option2-qa-normalized.png`
- Same-input comparison: `C:\Users\chris\OneDrive\Dokumente\Autobalancer\hll_rcon_tool-steam-enrichment\.tmp\product-design\live-game-option2-comparison.png`
- Source pixels: 1487 × 1058 at 1×.
- Implementation pixels: 2353 × 1272 at 1×; CSS browser viewport 2353 × 1272.
- Normalization: the implementation was downsampled proportionally to 1487 × 804 and placed on the same 1487 × 1058 dark canvas as the source. No crop or aspect distortion was applied.
- State: German dark Frontline theme, 36 simulated players, K/D descending, one selected player, player inspector visible, 17 rows per team.

## Full-view comparison

The normalized same-input comparison was reviewed for composition, hierarchy and density. The implementation preserves the selected option's command-board structure: flat match strip, shared command toolbar, mirrored allied/axis tables, central comparison rail and right-side player inspector. Main edges align, both team surfaces are symmetrical, selection is gold, faction meaning uses icon plus label, and the page avoids rounded nested cards.

The source is a 1487 px concept while the available in-app browser viewport is materially wider. The implementation intentionally uses the additional width instead of stretching type or rows; after proportional normalization, the major-region proportions and visual hierarchy remain equivalent. Responsive behavior is defined at 1440, 900 and mobile breakpoints; the current in-app browser did not expose a viewport override for a second pixel capture.

Focused region comparison was not necessary because the original-resolution implementation capture keeps the table headers, dense rows, center metrics and inspector typography legible. Those four regions were still reviewed separately at original resolution.

## Required fidelity surfaces

- Fonts and typography: passed. Existing Frontline display/body type is preserved; labels are uppercase with restrained tracking; player names remain lighter than headers; all metrics use tabular numerals.
- Spacing and layout rhythm: passed. Flat 1 px surfaces, 8–10 px major gaps, dense 34 px desktop rows, matched team widths, and an inspector aligned to the table block.
- Colors and tokens: passed. Existing theme tokens drive background, dividers and text; cyan/allied, muted red/axis, gold/selection and semantic warning/success tones match the reference intent.
- Image and icon fidelity: passed. Existing faction image assets and MUI icons are used. No custom SVG, CSS drawing, placeholder image or emoji was introduced in the redesigned page.
- Copy and content: passed with intentional product constraints. Squad and role are not shown because the live-game endpoint does not provide reliable values. Profile-safe actions are retained for disconnected historical match participants.

## Interaction verification

- Search filters both teams together and preserves symmetric sorting.
- All / active / flagged filters work.
- Row selection updates the player inspector.
- Checkbox selection enables the shared selection action.
- Both team pagers work independently; page-size selection is available.
- Sort field and direction are interactive.
- CSV export remains connected to the full filtered live-game dataset.
- Query refresh retains the 36-player demo dataset and next-map data.
- Page reload and 15-second refetch were tested without row-count collapse.
- Production build completed successfully.

## Comparison history

### Iteration 1 — blocked

- P2: the first build displayed all team rows and therefore lacked the mockup's compact footer/pagination rhythm.
- P2: the demo refresh replaced the dense 36-player initial state with six players and removed the next map.
- P2: sort direction and country used text/emoji-like glyph presentation instead of the selected icon language.

Fixes: independent team pagination, 17-row default page size, durable live-game Mirage data, stable next-map payload, MUI direction/public icons, uppercase mode label, and explicit unknown/offline status handling.

### Iteration 2 — passed

Post-fix evidence: `live-game-option2-qa.png` and `live-game-option2-comparison.png`. The mirrored table density, footer rhythm, persistent demo state, selection/inspector linkage and icon language now match the target without actionable P0/P1/P2 differences.

## Follow-up polish

- P3: capture dedicated 1000 px and 390 px screenshots when the in-app browser exposes viewport emulation; the implemented breakpoints already switch the inspector to a drawer and the teams to tabs.
- P3: a later backend enhancement could add reliable current squad/role data, but those values should not be inferred in this UI.

final result: passed
