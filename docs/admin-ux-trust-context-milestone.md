# Administrator UX milestone 1: trustworthy live context

## Problem

The dashboard previously rendered example values (`Foy`, `warfare`, a Frontline
server name, a night environment and `Online`) when the live API had not
provided those values. The header stayed in a loading skeleton when the
connection had already failed, and the sidebar reduced connection health to a
boolean. In a multi-server HLL/HLL Vietnam installation this could make stale
or missing data look current.

## Implemented vertical slice

- Model CRCON, game-server status and game-state transport health as `loading`,
  `online`, `offline`, `stale` or `unknown`.
- Preserve the last successful timestamp and mark cached data as stale after a
  failed refresh.
- Remove fabricated server, player, map, mode, environment and image fallbacks
  from the operational dashboard.
- Keep server number, server name and explicit HLL/HLL Vietnam identity visible
  in the persistent match-status bar.
- Give the compact header a responsive two-column layout for small screens.
- Explain CRCON and game-server states in German and English instead of showing
  raw English technical tooltips.
- Do not add API calls or polling loops; the existing 30-second queries expose
  their transport state through the shared store.

## Before/after evidence

### Before

- Missing data was represented by believable sample values.
- The dashboard always labelled the game server `Online` and `Healthy`.
- A failed refresh discarded status detail or left an endless skeleton.
- Game identity appeared only inside the server selector.

### After

- Missing fields explicitly display `Unknown` / `Unbekannt`.
- Connection loss, stale cached data and initial loading have distinct labels
  and colors, with text remaining the primary status signal.
- The dashboard shows the timestamp of the last successful game-server data.
- A missing or failed map image becomes a labelled unavailable state instead of
  silently displaying Foy.
- The persistent header identifies both supported games and the selected
  server.

Current-run screenshots still need to be added to the pull request. The Codex
in-app browser connector failed before it could read or modify the already open
`rcon3.fln.gg` tab. No older screenshot is being used as substitute evidence.

## Verification

- `pnpm test:unit`: 9 passing tests
  - query-state classification
  - stale-data behaviour
  - HLL/HLL Vietnam labels
  - German/English key parity
  - complete operational-state translations
- `pnpm build`: production frontend build succeeds with
  `REACT_APP_API_URL=/api/`.
- Main bundle from this build: 4,197.40 kB minified / 1,155.31 kB gzip.
- `git diff --check`: clean apart from the repository's existing Windows line
  ending notices.

## Manual test matrix required before merge

| Surface | HLL | HLL Vietnam | Multi-server | 390 px | 768 px | 1440 px |
| --- | --- | --- | --- | --- | --- | --- |
| Current data | pending | pending | pending | pending | pending | pending |
| Initial loading | pending | pending | pending | pending | pending | pending |
| CRCON offline | pending | pending | pending | pending | pending | pending |
| Game server offline | pending | pending | pending | pending | pending | pending |
| Failed refresh with cached data | pending | pending | pending | pending | pending | pending |

## Rollout and rollback

This milestone changes only frontend state interpretation and presentation. It
does not change game commands, permissions, API endpoints or polling frequency.
Rollback is the previous frontend image/tag. Production rollout remains blocked
until the screenshot and manual matrix above are complete and rollout is
explicitly approved.
