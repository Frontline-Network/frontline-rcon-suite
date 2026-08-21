# Discord moderation action matrix

This matrix is the operational contract between the Discord Report Bot and a
CRCON installation.  The offered actions are defined by
`rconweb.api.mobile_incidents.DISCORD_GAME_ACTIONS` and are exercised for both
supported games in `rconweb.api.tests.MobileContextTests`.

| Discord action | CRCON operation | HLL | HLL:V | Confirmation / outcome |
| --- | --- | --- | --- | --- |
| Message | `message_player` | one attempt | one attempt | no duplicate send after an ambiguous reply |
| Punish | `punish` | one attempt | one attempt | no duplicate punish after an ambiguous reply |
| Kick | `kick` | one attempt | verify offline, then one controlled retry | confirmation required; a verified offline player counts as completed |
| Temp ban | `temp_ban` | one attempt | verify ban, then one controlled retry | confirmation, reason and 1--720 hours required |
| Permanent ban | `perma_ban` | one attempt | verify ban, then one controlled retry | second Discord confirmation and a reason required |
| Blacklist | `add_blacklist_record` | one attempt | one attempt | second Discord confirmation, reason and blacklist ID required |
| Squad kick | `remove_player_from_squad` | one attempt | one controlled retry | confirmed player/squad and reason required |
| Disband squad | `disband_squad_by_name` | one attempt | one controlled retry | confirmed squad, reason and second Discord confirmation required |

For every action, CRCON revalidates the integration, guild, channel, current
Discord roles, incident revision and idempotency key. A rejected game action
does not resolve the incident. It is recorded in the incident timeline and is
rendered as a non-successful logbook entry in the Discord embed. Temporary
game-server errors are reported as pending confirmation rather than as an
invalid Discord interaction.
