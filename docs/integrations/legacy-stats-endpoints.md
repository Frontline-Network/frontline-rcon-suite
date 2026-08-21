# Retired Stats API endpoints

`/api/get_player_list` and `/api/get_scoreboard` are retired paths used by
older third-party bots. They return `410 Gone` rather than a guessed
compatibility payload. This prevents clients from silently interpreting a
different Frontline RCON Suite response as the old contract.

The response includes `Deprecation: true`, a `Link` header to the primary
replacement, `Retry-After: 300`, and a JSON migration payload whose
`documentation_endpoint` is `/api/get_api_documentation`. Clients should stop
polling the retired path and switch to the documented replacement.

| Retired path | Primary replacement | Alternatives |
| --- | --- | --- |
| `/api/get_player_list` | `/api/get_detailed_players` | `/api/get_players`, `/api/get_team_view` |
| `/api/get_scoreboard` | `/api/get_live_scoreboard` | `/api/get_scoreboard_maps`, `/api/get_map_scoreboard` |

Both retired paths are rate-limited per authenticated identity or client IP to
six requests per minute. A privacy-preserving, hashed client fingerprint is
logged at most once per endpoint and hour, so a stale bot cannot flood the
application logs while it is being migrated.
