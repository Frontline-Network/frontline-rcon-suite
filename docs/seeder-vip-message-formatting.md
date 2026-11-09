# Seeder VIP: precise reward messages

The friendly formatter used to turn a 36-hour reward into "a day" / "ein Tag".
The German relative expiry then became "ein Tag ab jetzt". Wrapping it in a
custom template's "in {vip_expiration} ab" produced the confusing message seen
on HLL1.

Friendly reward durations now retain hours, minutes and seconds without rounding
to days, months or years. A 36-hour reward reads "36 Stunden" in German or
"36 hours" in English. Relative expiry uses the player's actual expiration
timestamp, rounded only to the nearest minute. For German, the expiry variable
already includes "in" (or "vor" for a past expiry).

The raw duration/ISO-date options, VIP eligibility, cumulative rewards and the
actual expiration calculation are unchanged. Existing custom templates are not
automatically rewritten on upgrade.

## German template for HLL1

Use this with German friendly durations and relative expiry enabled:

```text
SEEDING BEENDET! Danke, dass du uns beim Seeden geholfen hast. Es gelten jetzt die normalen Spielregeln.

Deine VIP-Belohnung: {vip_reward}.
Dein VIP läuft {vip_expiration} ab.
```

Do not add another "in" before `{vip_expiration}`. At the inspected HLL1 setting
of 36 hours, a newly rewarded player sees "Deine VIP-Belohnung: 36 Stunden.
Dein VIP läuft in 36 Stunden ab." A player with existing VIP may have a longer
remaining duration; the message keeps reward and total remaining time distinct.

When deploying, back up HLL1's existing message and change only
`player_messages.reward_player_message` to the template above, preserving all
other settings. Do not send a live test announcement or grant VIP just to test
wording. This source change and template do not themselves deploy to HLL1.
