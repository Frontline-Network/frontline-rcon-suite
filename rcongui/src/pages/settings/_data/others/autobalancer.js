const autobalancerNotes = `
The fair autobalancer corrects persistent team-size differences while protecting
commanders, recent joins and established squads. The native HLL autobalancer remains
unchanged and should stay enabled as the first line of defence.

Modes:
- disabled: no planning or messages (upstream default)
- shadow: records proposals without messages or RCON actions (recommended pilot start)
- manual: asks for volunteers and requires an admin approval
- auto: asks for volunteers, then arms the selected player for a switch after death

For the FLN pilot set mode to "shadow" and configure history_server_numbers with all
FLN server numbers whose completed-map statistics may be used.
`;

export default autobalancerNotes;
