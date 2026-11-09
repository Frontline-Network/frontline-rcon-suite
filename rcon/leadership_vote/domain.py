"""Pure report, identity and event-time rules."""

import math
import re
from rcon.admin_incidents import _is_commander, _is_squad_leader, _normalize_team

OPEN = frozenset({"confirming", "warning", "inviting", "active", "executing"})
LIVE = OPEN
INVITATIONS = frozenset({"invite_de", "invite"})
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
    from rcon.user_config.report_admin import ReportAdminUserConfig

    text = str(log.get("sub_content") or "").strip()
    # Webhooks run before live target resolution. Keep reports handled by
    # Report Admin out of general chat mirrors; admin delivery stays intact.
    candidate = report_command(text)
    if not candidate:
        return False
    try:
        return ReportAdminUserConfig.load_from_db().enabled
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


def may_report(players, reporter_id, target):
    """Squad membership permits reporting, not voting or quorum participation.

    Check the current roster, not a report's possibly stale role/team. Members
    may report their own squad leader, but never themselves. Commanders may
    also report despite not belonging to a squad. Tenure applies only to voters.
    """
    reporter_id = str(reporter_id or "")
    if not reporter_id or reporter_id == target["player_id"]:
        return False
    matches = [p for p in players if str(p.get("player_id") or "") == reporter_id]
    if len(matches) != 1:
        return False
    player = matches[0]
    if (
        player.get("online") is False
        or _normalize_team(player.get("team")) != target["team"]
    ):
        return False
    squad = str(player.get("unit_name") or "").strip().casefold()
    return _is_commander(player) or squad not in {"", "unassigned", "command"}


def squad_target(subjects, reporter, players, message):
    from .targets import resolve

    resolved = resolve(message, subjects, reporter, players)
    if not resolved:
        return None
    p = resolved["player"]
    return dict(
        identity(p),
        player_id=str(p["player_id"]),
        name=str(p.get("name") or p.get("player_name") or ""),
        resolution=resolved["resolution"],
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
            "last_invited_at": None,
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
        text = (
            f"Dein Report / Your report: {target}\n"
            "Redet nicht? / Not communicating?\n"
            "!yes = Kick-Abstimmung starten / Start server-kick vote.\n"
            "!no = Abbrechen / Cancel.\n"
            f"Antworte in / Reply within {p['rules']['confirmation_seconds']} s."
        )
    elif purpose == "invite_de":
        prefix = (
            "PROBELAUF — kein automatischer Kick\n\n"
            if p["rules"]["mode"] == "dry_run"
            else ""
        )
        text = (
            f"FÜHRUNGSABSTIMMUNG\n{target}\n\n"
            f"Meldung: {clean_text(p.get('reason'), 160)}\n"
            "Diesen Spieler vom Server kicken?\n\n"
            "!yes = Für den Kick\n"
            "!no = Gegen den Kick\n\n"
            f"Du hast {p['rules']['duration_seconds']} Sekunden zum Antworten.\n"
            f"Benötigt: {p['required']} Ja-Stimmen bei "
            f"{p['participant_count']} stimmberechtigten Führungskräften."
        )
        channel = "\n\nAntworte nur im TEAM- oder SQUADCHAT."
    elif purpose == "invite":
        target = (
            f"Commander {who}"
            if p["target_role"] == "commander"
            else f"Squad {clean_text(p['squad'])} — Squad Leader {who}"
        )
        prefix = (
            "DRY RUN — no automatic kick\n\n" if p["rules"]["mode"] == "dry_run" else ""
        )
        text = (
            f"LEADERSHIP VOTE\n{target}\n\n"
            f"Report: {clean_text(p.get('reason'), 160)}\n"
            "Kick this player from the server?\n\n"
            "!yes = Vote to kick\n"
            "!no = Vote against kicking\n\n"
            f"You have {p['rules']['duration_seconds']} seconds to respond.\n"
            f"Required: {p['required']} YES votes out of "
            f"{p['participant_count']} eligible leaders."
        )
        channel = "\n\nReply in TEAM or SQUAD chat only."
    elif purpose == "ballot":
        text = f"{target}\nStimme gespeichert / vote recorded: {'Ja / Yes' if value else 'Nein / No'}."
    elif purpose == "result":
        text = f"{target}\n{p['result']}\nJa / Yes: {p['yes']}; Nein / No: {p['no']}; nötig / required: {p.get('required', '–')}."
    else:
        raise ValueError("Unknown message purpose")
    return prefix + text + (channel if purpose in {"confirm"} | INVITATIONS else "")
