"""Bounded, auditable case assessment. No model confidence is an action permit.

An accusation, a missing apology, repeated kills, or an unusual kill rate never
proves intent. Only a narrowly matched first-person admission linked to a real
teamkill can pass the automatic TK rule; conflicting context stays with admins.
Cheat assessments have no sanction path at all.
"""

import re
import time
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import joinedload

from rcon.game import get_game_profile
from rcon.models import LogLine, PlayerID, PlayerSession

LOOKBACK = 900
GRACE = 60
CASE_TTL = 180
MAX_ROWS = 2000

# Exact complete statements, not a keyword or an LLM's confidence. Quoted,
# negated, hypothetical, joking, third-person and qualified text cannot match.
ADMISSION = re.compile(
    r"(?:i (?:teamkilled|team killed) (?:you|him|her|them) (?:on purpose|intentionally)|"
    r"i intentionally (?:teamkilled|team killed) (?:you|him|her|them)|"
    r"ich habe (?:dich|ihn|sie|euch) absichtlich (?:geteamkillt|teamgekillt)|"
    r"ich hab (?:dich|ihn|sie|euch) absichtlich (?:geteamkillt|teamgekillt))",
    re.I,
)
APOLOGY = re.compile(
    r"(?:sorry(?: (?:for (?:the )?(?:tk|teamkill)|my bad|(?:about|for) that))?|"
    r"sry(?: (?:tk|teamkill))?|my bad|(?:sorry|sry)[ ,]+(?:tk|teamkill)|"
    r"(?:entschuldigung|entschuldige)(?: (?:für|fuer) (?:den )?(?:tk|teamkill))?|"
    r"(?:war |das war )?mein fehler|tut mir leid)",
    re.I,
)
EXPLOSIVE = {
    "grenade",
    "bazooka",
    "mine",
    "satchel",
    "pak",
    "armor",
    "artillery",
    "commander",
    "self_propelled_artillery",
}
# Review heuristics ONLY, in kills per wall-clock minute (not time in that role).
# Both complete 5- and 15-minute windows must exceed their category threshold.
# These are not calibrated cheating probabilities and never authorize a ban.
REVIEW_RATES = {
    "infantry": 3,
    "sniper": 3,
    "machine_gun": 5,
    "armor": 8,
    "artillery": 10,
}


def chat_body(content, name, pid):
    """Decode the recorder envelope exactly; never search names/IDs for intent."""
    prefix, suffix = f"{name}: ", f" ({pid})"
    if (
        isinstance(content, str)
        and content.startswith(prefix)
        and content.endswith(suffix)
    ):
        return content[len(prefix) : -len(suffix)]
    return None


def text_kind(body):
    if not isinstance(body, str) or len(body) > 300:
        return None
    text = body.strip().rstrip(".! ")
    if ADMISSION.fullmatch(text):
        return "admission"
    if APOLOGY.fullmatch(text):
        return "apology"
    return None


def weapon_category(weapon, game):
    game_name = {1: "hll", 2: "hllv"}.get(game)
    if not game_name:
        return "unknown"
    category = get_game_profile(game_name).weapons.get(weapon)
    return category.value if category else "unknown"


def fresh_logs(api):
    """Read current game logs, so a delayed DB recorder cannot hide an apology.

    Parsing failures or a capped response fail closed. This deliberately uses
    the same parser as both game adapters, but does not silently discard errors.
    """
    with api.without_retries():
        raw = api.get_logs(since_min_ago=20)
    if not isinstance(raw, list) or not all(isinstance(line, str) for line in raw):
        raise ValueError("Invalid live log response")
    parsed = api.parse_logs(raw)["logs"]
    if len(parsed) > 15000 or len(parsed) != len(list(api.split_raw_log_lines(raw))):
        raise ValueError("Incomplete live log response")
    return {
        "logs": parsed,
        "captured_at": time.time(),
        "game": int(api.config.game.to_int()),
    }


def collect(sess, server, payload, reporter_id, now, live):
    """Combine server/round/session-scoped persisted and freshly fetched facts."""
    sessions = [
        sess.get(PlayerSession, payload[key]) for key in ("session", "reporter_session")
    ]
    starts = [
        s.start.replace(tzinfo=timezone.utc).timestamp()
        for s in sessions
        if s and s.start
    ]
    start = max(payload["round_start"], payload["report_time"] - LOOKBACK, *starts)
    ids = set(
        sess.scalars(
            select(PlayerID.id).where(
                PlayerID.player_id.in_([payload["target_id"], reporter_id])
            )
        )
    )
    rows = sess.scalars(
        select(LogLine)
        .options(joinedload(LogLine.player_1), joinedload(LogLine.player_2))
        .where(
            LogLine.server == str(server),
            LogLine.event_time
            >= datetime.fromtimestamp(start, timezone.utc).replace(tzinfo=None),
            LogLine.event_time
            <= datetime.fromtimestamp(now, timezone.utc).replace(tzinfo=None),
            or_(LogLine.player1_player_id.in_(ids), LogLine.player2_player_id.in_(ids)),
        )
        .order_by(LogLine.event_time, LogLine.id)
        .limit(MAX_ROWS + 1)
    ).all()
    facts, malformed = {}, False
    database_keys, live_keys = set(), set()

    def add(
        stamp,
        action,
        actor,
        victim,
        name,
        victim_name,
        weapon,
        body,
        game,
        log_id=None,
        from_live=False,
    ):
        nonlocal malformed
        if not start <= stamp <= now or not {actor, victim}.intersection(
            {payload["target_id"], reporter_id}
        ):
            return
        if action not in {"KILL", "TEAM KILL"} and not str(action).startswith("CHAT["):
            return
        if not actor or (action in {"KILL", "TEAM KILL"} and not victim):
            malformed = True
            return
        if str(action).startswith("CHAT[") and body is None:
            malformed = True
        weapon = weapon or ""
        key = (stamp, action, actor, victim, weapon, body)
        (live_keys if from_live else database_keys).add(key)
        if key not in facts:
            facts[key] = {
                "at": stamp,
                "type": action,
                "actor": actor,
                "victim": victim,
                "name": str(name or actor)[:100],
                "victim_name": str(victim_name or victim or "")[:100],
                "weapon": str(weapon or "")[:120],
                "category": weapon_category(weapon, game),
                "body": (body[:400] if body is not None else None),
                "log_id": log_id,
            }
        elif log_id:
            facts[key]["log_id"] = log_id

    for row in rows[:MAX_ROWS]:
        actor = row.player_1.player_id if row.player_1 else None
        victim = row.player_2.player_id if row.player_2 else None
        add(
            row.event_time.replace(tzinfo=timezone.utc).timestamp(),
            row.type,
            actor,
            victim,
            row.player1_name,
            row.player2_name,
            row.get_weapon(),
            (
                chat_body(row.content, row.player1_name, actor)
                if str(row.type).startswith("CHAT[")
                else None
            ),
            row.game,
            row.id,
        )
    live_ok = isinstance(live, dict) and 0 <= now - live.get("captured_at", 0) <= 10
    if live_ok:
        for row in live["logs"]:
            add(
                row["timestamp_ms"] / 1000,
                row["action"],
                row.get("player_id_1"),
                row.get("player_id_2"),
                row.get("player_name_1"),
                row.get("player_name_2"),
                row.get("weapon"),
                (
                    row.get("sub_content")
                    if str(row["action"]).startswith("CHAT[")
                    else None
                ),
                live.get("game"),
                from_live=True,
            )
    complete = (
        live_ok
        and len(rows) <= MAX_ROWS
        and not malformed
        and database_keys.issubset(live_keys)
    )
    return {
        "facts": sorted(facts.values(), key=lambda x: (x["at"], x["log_id"] or 0)),
        "start": start,
        "end": now,
        "complete": complete,
        "limitations": (
            []
            if complete
            else [
                "Stale, incomplete or unparseable logs / Veraltete, unvollständige oder unlesbare Logs"
            ]
        ),
    }


def assess_teamkills(case, target, reporter, report_time, now):
    facts = case["facts"]
    tks = [f for f in facts if f["type"] == "TEAM KILL" and f["actor"] != f["victim"]]
    outgoing = [f for f in tks if f["actor"] == target]
    reported = [f for f in outgoing if f["at"] <= report_time]
    chats = [
        f for f in facts if f["actor"] == target and str(f["type"]).startswith("CHAT[")
    ]
    apologies = [
        f
        for f in chats
        if text_kind(f["body"]) == "apology"
        and any(0 <= f["at"] - k["at"] <= GRACE for k in outgoing)
    ]
    admissions = [
        f
        for f in chats
        if text_kind(f["body"]) == "admission"
        and any(0 <= f["at"] - k["at"] <= GRACE for k in reported)
    ]
    reporter_kills = [f for f in tks if f["actor"] == reporter and reporter != target]
    reciprocal = [
        f
        for f in tks
        if f["victim"] == target and any(k["victim"] == f["actor"] for k in outgoing)
    ]
    deadline = max((f["at"] + GRACE for f in outgoing), default=now)
    timeline = [
        f
        for f in facts
        if f["type"] == "TEAM KILL" or str(f["type"]).startswith("CHAT[")
    ]
    assessment = {
        "kind": "teamkill_case",
        "apologies": [f["log_id"] for f in apologies],
        "admissions": [f["log_id"] for f in admissions],
        "reporter_teamkills": len(reporter_kills),
        "reciprocal_teamkills": len(reciprocal),
        "kills_after_apology": sum(
            any(k["at"] > a["at"] for a in apologies) for k in outgoing
        ),
        "possible_explosion_bursts": sum(
            k["category"] in EXPLOSIVE
            and any(
                o is not k
                and o["weapon"] == k["weapon"]
                and abs(o["at"] - k["at"]) <= 2
                for o in outgoing
            )
            for k in outgoing
        ),
        "timeline": timeline if len(timeline) <= 40 else timeline[:10] + timeline[-30:],
        "timeline_omitted": max(0, len(timeline) - 40),
        "limitations": case["limitations"],
    }
    evidence = {
        "teamkill_count": len(outgoing),
        "teamkill_log_ids": [f["log_id"] for f in outgoing if f["log_id"]][:50],
        "window_seconds": int(now - case["start"]),
        "assessment": assessment,
        "ready_at": deadline,
    }
    if not case["complete"]:
        return (
            "manual",
            "Daten nicht vollständig prüfbar / Cannot validate complete evidence",
            evidence,
        )
    if not reported:
        return (
            "manual",
            "Kein zugehöriger Teamkill belegt / No matching teamkill recorded",
            evidence,
        )
    if now < deadline:
        return (
            "waiting",
            "Stille 60-Sekunden-Prüffrist / Silent 60-second observation window",
            evidence,
        )
    if reporter_kills or reciprocal:
        return (
            "manual",
            "Beide Seiten beteiligt; Admins prüfen Reihenfolge / Both sides involved; admins review chronology",
            evidence,
        )
    if apologies:
        return (
            "manual",
            "Entschuldigung im Kontext prüfen; weitere TK sind kein Absichtsbeweis / Review apology and subsequent kills; repetition alone does not prove intent",
            evidence,
        )
    # An admission followed/accompanied by additional ambiguous text must not
    # overrule a retraction, joke, quotation or explanation in that same window.
    other_context = [
        f
        for f in chats
        if not text_kind(f["body"])
        and not str(f["body"] or "").lower().startswith("!admin ")
        and any(abs(f["at"] - a["at"]) <= GRACE for a in admissions)
    ]
    if admissions and other_context:
        return (
            "manual",
            "Zusätzlicher Chatkontext erfordert Prüfung / Additional chat context requires review",
            evidence,
        )
    if admissions:
        return (
            "eligible",
            "Teamkill mit zeitnaher ausdrücklicher eigener Absichtserklärung / Recorded teamkill with a timely explicit first-person admission",
            evidence,
        )
    return (
        "manual",
        "Absicht nicht sicher belegt; Anzahl oder Schweigen reichen nicht / Intent unproven; count or silence is insufficient",
        evidence,
    )


def assess_cheating(case, target, role_history=None):
    facts, end = case["facts"], case["end"]
    kills = [
        f
        for f in facts
        if f["type"] == "KILL" and f["actor"] == target and f["victim"] != target
    ]
    deaths = [f for f in facts if f["type"] == "KILL" and f["victim"] == target]
    windows = []
    for seconds in (60, 300, 900):
        observed = min(seconds, end - case["start"])
        sample = [f for f in kills if f["at"] > end - seconds]
        by_category = Counter(f["category"] for f in sample)
        windows.append(
            {
                "seconds": seconds,
                "observed_seconds": int(observed),
                "kills": len(sample),
                "deaths": sum(f["at"] > end - seconds for f in deaths),
                "distinct_victims": len({f["victim"] for f in sample}),
                "categories": dict(by_category),
                "rates": (
                    {k: round(v * 60 / observed, 2) for k, v in by_category.items()}
                    if observed
                    else {}
                ),
            }
        )
    reasons = []
    for category, threshold in REVIEW_RATES.items():
        if all(
            w["observed_seconds"] == w["seconds"]
            and w["rates"].get(category, 0) > threshold
            for w in windows[1:]
        ):
            reasons.append(
                f"{category}: > {threshold} kills/min in both 5- and 15-minute windows (review heuristic, not proof)"
            )
    insufficient = (
        not case["complete"]
        or not kills
        or end - case["start"] < 300
        or any(f["category"] == "unknown" for f in kills)
    )
    state = (
        "suspicious"
        if reasons and case["complete"]
        else "insufficient_data" if insufficient else "no_observed_anomaly"
    )
    labels = {
        "suspicious": "Auffällige Killrate: Admin-Beobachtung priorisieren; kein Cheatnachweis / Unusual kill rate: prioritize admin observation; not proof of cheating",
        "insufficient_data": "Daten für Cheatbewertung unzureichend / Insufficient evidence for cheat assessment",
        "no_observed_anomaly": "Keine Auffälligkeit nach diesen begrenzten Kriterien; kein Freispruch / No anomaly under these limited checks; not exoneration",
    }
    history = (role_history or [])[-40:]
    return (
        "manual",
        labels[state],
        {
            "window_seconds": int(end - case["start"]),
            "assessment": {
                "kind": "cheat_review",
                "state": state,
                "priority": "high" if state == "suspicious" else "normal",
                "reasons": reasons,
                "windows": windows,
                "weapons": dict(Counter(f["weapon"] for f in kills)),
                "multikill_candidates": [
                    {"at": f["at"], "weapon": f["weapon"], "category": f["category"]}
                    for f in kills
                    if any(
                        k is not f
                        and k["weapon"] == f["weapon"]
                        and abs(k["at"] - f["at"]) <= 2
                        for k in kills
                    )
                ][:40],
                "timeline": kills[-20:],
                "timeline_omitted": max(0, len(kills) - 20),
                "role_history": history,
                "limitations": case["limitations"]
                + (
                    ["Role history unavailable / Rollenverlauf nicht verfügbar"]
                    if not history
                    else []
                )
                + [
                    "Weapon classification per kill; rates use observation time, not role duration. No aim/visibility evidence. / Waffen je Kill; keine Ziel- oder Sichtdaten."
                ],
                "automatic_sanction": False,
                "manual_ban_hours": 24,
            },
        },
    )
