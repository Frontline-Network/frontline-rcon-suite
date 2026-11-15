"""Prepare conservative transition holds while automod workers are stopped."""
from sqlalchemy import select

from rcon.automods import action_guard


def bootstrap(server_number: int, moderators) -> dict:
    """Hold each enabled live rule until an operator checks prior outcomes.

    The caller MUST first stop every automod worker for this server and keep
    them stopped until all holds are committed and the new version is active.
    """
    rules = []
    for mod in moderators:
        if mod.config.dry_run:
            continue
        rule = getattr(mod, "action_author", None)
        if not isinstance(rule, str) or not rule:
            raise ValueError("Enabled automod lacks a stable rule identity")
        rules.append(rule)
    rules = sorted(set(rules))
    created = 0
    for rule in rules:
        token = action_guard.reserve(server_number, "*", [rule], "message", legacy_global=True)
        if token:
            created += 1
    with action_guard.get_session_maker()() as session:
        present = set(session.scalars(select(action_guard.action_guard.c.rule).where(
            action_guard.action_guard.c.server_number == server_number,
            action_guard.action_guard.c.player_id == "*",
            action_guard.action_guard.c.state == "pending",
            action_guard.action_guard.c.rule.in_(rules))).all()) if rules else set()
    if present != set(rules):
        raise RuntimeError("Not all enabled automod rules have transition holds")
    return {"enabled_live_rules": len(rules), "new_holds": created}
