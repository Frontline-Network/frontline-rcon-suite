"""Pure report, identity and event-time rules."""

import math
import re
from rcon.admin_incidents import _is_commander, _is_squad_leader, _normalize_team

OPEN = frozenset({"confirming", "warning", "inviting", "active", "executing"})
LIVE = OPEN
MAX_EVENT_AGE = 30
MAX_OBSERVATION_GAP = 15


def answer(message):
    return {"!yes": True, "!no": False}.get(str(message or "").strip().casefold())


def event_time(log):
    try:
        stamp = float(log["timestamp_ms"]) / 1000
        return stamp if math.isfinite(stamp) else None
    except (KeyError, TypeError, ValueError):
        return None


def private_chat(log, team=None):
    # Unknown/global channels fail closed for both games.
    kind = str(log.get("type") or log.get("action") or "")
    match = re.fullmatch(r"CHAT\[(Allies|Axis)\]\[(Team|Unit)\]", kind, re.I)
    return bool(
        match and (team is None or _normalize_team(team) == match[1].casefold())
    )


def report_command(message):
    return bool(re.match(r"^\s*!admin\b", str(message or ""), re.I))


def suppress_public_chat(log):
    from rcon.user_config.leadership_vote import LeadershipVoteUserConfig

    text = str(log.get("sub_content") or "").strip()
    # Webhooks run before live target resolution. Any !admin report may now
    # offer a private workflow, including reports without a written reason.
    # Keep all such reports out of general chat mirrors; admin delivery stays.
    candidate = answer(text) is not None or report_command(text)
    if not candidate:
        return False
    try:
        return LeadershipVoteUserConfig.load_from_db().enabled
    except Exception:
        return True  # do not disclose possible team proceedings during an outage


def identity(player):
    if not player or not player.get("player_id"):
        return None
    team = _normalize_team(player.get("team"))
    if team not in {"allies", "axis"}:
        return None
    commander = _is_commander(player)
    if not commander and not _is_squad_leader(player):
        return None
    squad = str(player.get("unit_name") or "")
    if not commander and not squad:
        return None
    return {
        "team": team,
        "role": re.sub(r"[^a-z0-9]", "", str(player.get("role") or "").casefold()),
        "kind": "commander" if commander else "squadleader",
        "squad": "" if commander else squad,
        "squad_id": "" if commander else str(player.get("unit_id") or squad),
    }


def leader(player, team):
    ident = identity(player)
    return bool(ident and ident["team"] == team)


def squad_target(subjects, reporter, players):
    """Resolve exactly one confirmed own-team squad or commander; no fuzzy targets."""
    team = _normalize_team((reporter or {}).get("team"))
    candidates = [s for s in subjects if s.get("state") != "rejected"]
    if team not in {"allies", "axis"} or len(candidates) != 1:
        return None
    subject = candidates[0]
    if (
        subject.get("state") != "confirmed"
        or _normalize_team(subject.get("team")) != team
    ):
        return None
    if subject.get("kind") == "squad" and subject.get("match_method") == "squad_exact":
        matching = [
            p
            for p in players
            if (i := identity(p))
            and i["team"] == team
            and i["kind"] == "squadleader"
            and i["squad"] == subject.get("squad_name")
        ]
        expected = subject.get("leader_player_id")
    elif (
        subject.get("kind") == "player"
        and subject.get("match_method") == "team_commander"
    ):
        matching = [
            p
            for p in players
            if (i := identity(p)) and i["team"] == team and i["kind"] == "commander"
        ]
        expected = subject.get("player_id")
    else:
        return None
    if len(matching) != 1 or str(matching[0].get("player_id")) != str(expected):
        return None
    p = matching[0]
    return dict(
        identity(p),
        player_id=str(expected),
        name=str(p.get("name") or p.get("player_name") or ""),
    )


def electorate(players, target, presence, now, tenure):
    result = {}
    # Incomplete/duplicate leadership seats cannot manufacture extra votes.
    seats = {}
    for p in players:
        ident = identity(p)
        if ident:
            seats.setdefault(
                (ident["team"], ident["kind"], ident["squad_id"]), []
            ).append(p)
    for members in seats.values():
        if len(members) != 1:
            continue
        p = members[0]
        pid, ident = str(p["player_id"]), identity(p)
        observation = presence.get(pid)
        if (
            ident["team"] != target["team"]
            or pid == target["player_id"]
            or (
                target["kind"] == "squadleader"
                and ident["squad_id"] == target["squad_id"]
            )
            or not observation
            or observation["identity"] != ident
            or not 0 <= now - observation["seen_at"] <= MAX_OBSERVATION_GAP
            or now - observation["since"] < tenure
        ):
            continue
        result[pid] = {
            "name": str(p.get("name") or ""),
            "identity": ident,
            "token": observation["token"],
            "invited_at": None,
            "valid": True,
        }
    return result


def clean_text(value, limit=100):
    return re.sub(r"[\x00-\x1f\x7f]+", " ", str(value or ""))[:limit]


def message(vote, purpose, value=None):
    p = vote.payload
    who = clean_text(p["target_name"])
    target = (
        f"Commander {who}"
        if p["target_role"] == "commander"
        else f"Squad {clean_text(p['squad'])} – Squadleader {who}"
    )
    prefix = (
        "PROBELAUF / DRY RUN – kein automatischer Kick / no automatic kick\n"
        if p["rules"]["mode"] == "dry_run"
        else ""
    )
    channel = "\nNur Team-/Squadchat / Team or squad chat only."
    if purpose == "confirm":
        text = f"{target}\nGeht es um fehlende Kommunikation? Mit !yes bestätigen: erst Warnung, dann Abstimmung über Server-Kick.\nIs this about missing communication? Confirm with !yes: warning first, then a server-kick vote.\nAnderer Grund / Other reason: !no. Admin-Report bleibt offen / Admin report stays open.\n{p['rules']['confirmation_seconds']} Sekunden / seconds. Bestätigung ist keine Stimme / Confirmation is not a ballot."
    elif purpose == "target":
        text = f"{target}\nDu wurdest als nicht erreichbar gemeldet. Melde dich im Führungskanal oder gib die Rolle ab.\nYou were reported as unresponsive. Speak in leadership voice chat or give up the role.\n{p['rules']['warning_seconds']} Sekunden / seconds; danach Vote über Server-Kick / then server-kick vote."
    elif purpose == "warning":
        text = f"{target}\nWarnung zugestellt. Bei Klärung mit !no zurückziehen.\nWarning delivered. If resolved, withdraw with !no.\n{p['rules']['warning_seconds']} Sekunden / seconds."
    elif purpose == "invite":
        text = f"{target}\nWegen fehlender Kommunikation vom Server kicken?\nKick from server for not communicating?\n!yes = Ja / Yes; !no = Nein / No\n{p['rules']['duration_seconds']} Sekunden / seconds. Nötig / required: {p['required']} Ja / yes von / out of {p['participant_count']}."
    elif purpose == "ballot":
        text = f"{target}\nStimme gespeichert / vote recorded: {'Ja / Yes' if value else 'Nein / No'}."
    elif purpose == "result":
        text = f"{target}\n{p['result']}\nJa / Yes: {p['yes']}; Nein / No: {p['no']}; nötig / required: {p.get('required', '–')}."
    else:
        raise ValueError("Unknown message purpose")
    return (
        prefix + text + (channel if purpose in {"confirm", "warning", "invite"} else "")
    )
