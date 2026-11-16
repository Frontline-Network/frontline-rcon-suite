# Automod action guard

Before an automatic warning, punishment or kick is sent, its originating rules reserve a durable per-server, per-player action guard in PostgreSQL. A confirmed response or explicit rejection clears the pending state only after the existing rule watch has recorded the result. A timeout, unrecognised response, interrupted process or failure to record the outcome leaves the guard pending. While it is pending, subsequent warnings, punishments and kicks from the same rule for that player are suppressed, even if its Redis watch expires or the player reconnects. Other servers and unrelated rules remain independent. If the database is unavailable, automatic actions fail closed. Simulation mode does not reserve or send a real action.

Operators with player-profile viewing rights can inspect pending actions on the player-records page. Releasing a guard additionally requires raw-command permission, explicit confirmation and a reason. The reservation, result and review are recorded in a separate history table. Before release, inspect available evidence and ensure the original request is no longer running. Releasing permits the rule to act again; it does not prove the previous action was or was not delivered. Pending entries are not expired automatically.

For a safe transition from older workers, stop every automod worker for the server before creating rule-wide transition holds for its enabled live rules. The holds use the reserved player identifier `*`, display as applying to all players of the rule, and require the same audited review. Keep workers stopped until all holds are committed and the upgraded worker is ready. Older workers do not consult the new guard; restarting one reintroduces the earlier risk. A transition hold can temporarily suppress a whole rule, including otherwise legitimate moderation, until an administrator has reviewed it. Never create a rule-wide hold concurrently with running old workers.

Delayed connect warnings use the same guard: a lost or ambiguous reply retains the reservation across reconnects, while an explicit rejection allows a subsequent attempt. The migration adds `automod_action_guard` and `automod_action_guard_history`; do not drop them during a runtime rollback. Their pending and audit records are part of the PostgreSQL backup. Old records that expired before the transition cannot be reconstructed reliably. Other side-effect commands require separate review; this guard is not a claim that every possible duplicate side effect has been eliminated.

Seeding weapon violations also retain the identity of the originating log event, so a confirmed or reviewed action cannot be repeated for the same event and rule. An explicit rejection permits another attempt. On the first observed violation after this protection is introduced, the server establishes a transition boundary and suppresses actions for at least one minute; a clock difference can extend the hold. Events more than one minute ahead of the RCON clock or more than 24 hours old are skipped. Finalized event records older than seven days are eligible for cleanup; pending records remain until reviewed. Reviewing an uncertain action permits later events, but does not allow replay of the reviewed event. The event tables and their transition boundary must be retained during rollback, and all automod workers for the server must use the protection for it to be effective.

## Blacklist enforcement transition

The `BlacklistEnforcement` rule guards blacklist kicks and bans whose results are uncertain. Blacklist synchronization is serialized with connection-time enforcement and pauses for a player while an earlier result for that player remains pending. A global transition hold also pauses new blacklist enforcement and synchronization, including removals. Existing game-server bans are not actively removed by creating this hold. Journal entries affected during the hold can require a separate manual review; releasing the hold does not automatically resolve every queued change.

The hold is **not created automatically by an upgrade**. Before upgrading an existing server, stop all of its old backend and supervisor workers, including any other workers that can enforce or synchronize blacklist actions. After the guard tables and supported action constraint have been installed, but before starting upgraded workers, create and verify the global hold for that server:

```python
from rcon.automods import action_guard

server_number = 3  # Replace with the actual target server number.
action_guard.reserve(server_number, "*", ["BlacklistEnforcement"], "ban", legacy_global=True)
assert "*" in action_guard.pending_players(server_number, "BlacklistEnforcement")
```

Keep older workers stopped: they do not honor this guard. Review the available evidence for earlier uncertain requests and queued synchronization changes before an authorized operator releases the hold with an audited reason. A missing or incomplete history cannot prove that a request had no effect. If the upgrade fails after the hold is created, do not restart an older worker as an automatic rollback: it could bypass the hold. Recover using guarded workers or make a separately reviewed operational decision. All producers and target workers sharing blacklist data must also use durable synchronization; this guard alone does not upgrade older services.
