# Queue diagnostics and slot-write protection

Queue length and reserved VIP slots are read **directly from the game server**
before being set. Identical values are not written again; a failed read never
causes a blind write. The UI's ten-minute settings cache is not used to make
this decision. This applies to both HLL and HLLV, manual commands, Auto Settings
and Real VIP. The desired settings and normal configuration interfaces do not
change. There is no claim that repeated writes caused the observed HLLV stalls.

The per-server routines process runs a read-only queue watchdog every 30 seconds
in both split and shared supervisor modes. It warns about a **possible** admission
stall only after three minutes of consecutive valid observations with waiting
players, at least two free public slots (after subtracting all VIP reservations),
and no newly observed player IDs. Players leaving do not count as admission
progress; newly observed players reset the timer even if total occupancy is
unchanged. This is a sampled indication, not proof about individual queue positions.

Safety guards:

- A recorder-confirmed, ongoing round must match the live map before and after
  collection. The first three minutes of a round are excluded. New round IDs or
  a rising match timer trigger a new grace period, including same-map restarts.
- Missing, slow, inconsistent or implausible observations (including `7/6`),
  changed slot limits, observation gaps over 90 seconds and process restarts
  discard accumulated evidence. Unknown state is not recovery or a stall alarm.
- The raw `vipQueueCount` field is deliberately not used: during the observed
  HLLV incident it matched the entire registered VIP list, not online VIPs.
- All game-server commands used by the watchdog are `GetServerInformation` reads.
  It never kicks, messages players, changes slots, resets a queue or restarts anything.

One bilingual German/English notice is logged and queued to the existing **audit
Discord webhooks** per uninterrupted incident. A per-server Redis reservation
limits notices to one per 15 minutes, surviving runtime restarts and preventing
duplicate/uncertain delivery retries. With no audit webhook configured, the
warning remains in the routines/combined-runtime log; no new webhook or mention
recipient is created automatically. Notification failures never stop other routines.

An expiring, player-ID-free diagnostic status is stored in the server's Redis DB
at `queue_watchdog:<server_number>:status` (120-second TTL). States are `unknown`,
`round_grace`, `normal`, `observing`, or `suspected_stall`. This is operational
diagnostic data, not a new public API or frontend indicator.

The watchdog is enabled by default. Set `HLL_QUEUE_WATCHDOG_ENABLED=false` on
the relevant supervisor to disable it; slot write protection remains in effect.
No database migration or existing server-setting change is required.
