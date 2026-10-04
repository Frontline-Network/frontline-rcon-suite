# Release highlights / „Was ist neu?“

Release notes remain the technical record. Add a short, reviewed German and
English spotlight when a release includes a change operators should discover.
Do not announce every fix or generate summaries dynamically in the browser.

## Authoring

Append exactly one hidden JSON block to the private GitHub release body:

```markdown
<!-- crcon-highlights
{
  "schema_version": 1,
  "title": { "de": "Dein RCON. Dein Look.", "en": "Your RCON. Your style." },
  "description": {
    "de": "Wähle deinen Farbstil und richte deinen Arbeitsbereich passend ein.",
    "en": "Choose your colours and make the workspace your own."
  },
  "image": "theme-collection",
  "image_alt": { "de": "RCON-Ansichten in sechs Farbstilen.", "en": "RCON dashboards in six colour styles." },
  "action": { "id": "appearance", "label": { "de": "Darstellung öffnen", "en": "Open appearance" } },
  "items": [
    {
      "icon": "shortcuts",
      "title": { "de": "Schneller ans Ziel", "en": "Get there faster" },
      "description": { "de": "Lege deine wichtigsten Aurora-Schnellzugriffe selbst fest.", "en": "Choose your own Aurora shortcuts for frequently used pages." }
    }
  ]
}
-->
```

This is an authoring example, not a claim that these changes belong to an existing
published release. The local Mirage preview uses clearly labelled synthetic copy.
Only add accurate copy for the release being prepared; do not retrofit unrelated
features into older release notes.

- All copy, including image alternatives and button labels, requires both `de`
  and `en`. The app selects its current language. Plain text only; no Markdown or
  HTML is rendered inside the spotlight.
- Limits: title 100 characters, description 320, action label 60, image alternative
  180. Up to two supporting items, each with title 100 and description 240.
- `image` is optional; the only registered image is `theme-collection`. New assets
  must be shipped with the frontend and registered in both server validation and
  `ReleaseHighlightsDialog.jsx`. Remote URLs are not accepted.
- `action` is optional. Allowed IDs: `appearance`, `documentation`, `overview`.
  These map to built-in app destinations, not arbitrary release-supplied URLs.
- Item icons: `shortcuts`, `book`, `palette`, `overview`. `items` may be empty.
- Invalid, oversized (>16,000 characters), duplicate or incomplete blocks do not
  produce a spotlight. The technical notes still display without the metadata.

## Build and deployment

The existing `scripts/sync_release_notes.py` workflow copies release bodies into
the backend snapshot. Therefore no browser GitHub access, additional runtime
credential or separate announcement service is required. Include the block before
syncing the release notes for the final image. Backend migration
`0040_user_release_highlight_state` is required with this implementation.

Both frontend and backend must report the same exact published version. Only that
release can trigger a spotlight; drafts, future versions, development versions,
incomplete rollouts and older history entries cannot trigger one. Publish and
sync release content through the existing release process. Do not bypass version
verification for a demo or local development build.

## Operator behaviour

The automatic spotlight waits for an idle overview (`/`), a visible document and
no other dialog, menu, focused input or mutation. Other routes never auto-open it.
It is available manually in the account menu and update channel in both themes.

The backend keeps one record per user and normalized release version. An atomic
`claim` marks it seen before opening, preventing duplicate announcements from
concurrent tabs/devices. If that tab closes during loading, automatic presentation
is not retried; the manual entry remains available. Closing or following an action
keeps it seen. `later` clears seen and snoozes for 24 hours. Manual reopening marks
it seen again and cancels a snooze. Changelog read status remains separate.

`GET /api/get_update_channel?frontend_version=…` includes `highlights` in eligible
release entries and `highlight_state` for the current release. The latter contains
`release_version`, `seen`, `snoozed_until`, and `auto_show` (or is null).

`POST /api/set_own_release_highlight_state` takes exactly `frontend_version`,
`release_version`, `action` (`claim`, `seen`, `later`). It only modifies the signed-in
account, requires normal session CSRF protection and returns a private, uncached
response. `show` is true only for a successful eligible claim. Errors: 400 invalid
payload, 401 unauthenticated, 403 failed session CSRF, 405 wrong method, 409 version
or content not eligible. There is no game-server mutation or new permission grant.
