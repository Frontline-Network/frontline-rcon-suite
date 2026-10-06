"""Conservative report classification; text is data, never an instruction.

Only two rules are supported. Unsupported wording is a manual report, not a
best-guess sanction. Communication is a reported allegation, not voice evidence.
"""

import re

from rcon.admin_incidents import _normalize_message, _normalize_team
from rcon.leadership_vote.domain import identity, may_report
from rcon.leadership_vote.targets import resolve, LETTERS, COMMANDERS, SQUAD_TYPOS

TEAMKILL_COUNT = 5
TEAMKILL_SECONDS = 300
MAX_REPORT_AGE = 60

COMMUNICATION = re.compile(
    r"\b(?:redet nicht|spricht nicht|kommuniziert nicht|keine? (?:komms?|comms?|kommunikation)|"
    r"not (?:talking|communicating|speaking)|does not (?:talk|communicate|speak)|"
    r"no (?:comms?|communication)|doesn t (?:talk|communicate|speak))\b"
)
TEAMKILLS = re.compile(
    r"\b(?:teamkills?|teamkillt|teamkilling|teamkiller|tk|tks|tk[st]|team killed|team killing)\b"
)
# A mixed/qualified complaint is deliberately not sufficient for direct action.
QUALIFIED = re.compile(
    r"\b(?:nicht mehr|doch|wieder|aber|vielleicht|angeblich|sagt|sagte|behauptet|"
    r"kein teamkill\w*|keine teamkills|nicht teamkill\w*|kein tk|keine tks|nicht kicken|"
    r"not anymore|anymore|but|maybe|says|said|claims|accident|accidental|"
    r"aus versehen|versehentlich|not teamkill\w*|no teamkill\w*|don t kick|"
    r"cheat\w*|hack\w*|sabot\w*|beleidig\w*)\b"
)


def classify(message, players=()):
    match = re.match(r"^\s*!admin\b", str(message or ""), re.I)
    if not match:
        return None
    raw = str(message)[match.end() : 4000]
    if any(c in raw for c in ('"', "?", "“", "”")):
        return None
    text = _normalize_message(raw)
    # A player's name must not manufacture a complaint (e.g. "No Comms").
    for p in sorted(players, key=lambda p: len(str(p.get("name") or "")), reverse=True):
        name = _normalize_message(str(p.get("name") or p.get("player_name") or ""))
        if name:
            text = re.sub(r"(?<!\w)" + re.escape(name) + r"(?!\w)", " ", text)
    if QUALIFIED.search(text) or any(c in text for c in ('"', "?", "“", "”")):
        return None
    comm, tk = bool(COMMUNICATION.search(text)), bool(TEAMKILLS.search(text))
    if comm == tk:
        return None
    return "communication" if comm else "teamkills"


def target_for(incident, players, rule, *, allow_self_reports=False):
    """Accept exact references or independently validated, unique name typos."""
    ids = [str(p.get("player_id") or "") for p in players]
    if not all(ids) or len(ids) != len(set(ids)):
        return None
    reporter = next(
        (p for p in players if str(p.get("player_id")) == incident.get("reporter_id")),
        None,
    )
    if not reporter or reporter.get("online") is False:
        return None
    if rule == "communication":
        found = resolve(
            incident.get("raw_message"), incident.get("subjects", []), reporter, players
        )
        if not found:
            if has_role_reference(incident.get("raw_message"), players):
                return None  # A conflicting/absent squad is not a name fallback.
            p = exact_player(
                incident.get("subjects", []), players
            ) or conservative_name_match(incident.get("subjects", []), players)
            if not p:
                return None
        else:
            p = found["player"]
        if any(
            s.get("state") == "rejected"
            or (s.get("player_id") and str(s["player_id"]) != str(p["player_id"]))
            for s in incident.get("subjects", [])
        ):
            return None
        seat = identity(p)
        if (
            not seat
            or not unique_seat(players, seat)
            or not (
                (
                    allow_self_reports
                    and str(p["player_id"]) == incident.get("reporter_id")
                )
                or may_report(
                    players,
                    incident.get("reporter_id"),
                    dict(seat, player_id=str(p["player_id"])),
                )
            )
        ):
            return None
    else:
        # Only a single exact or independently verified current player. A squad
        # reference must never attribute all member teamkills to its leader.
        subjects = incident.get("subjects") or []
        if len(subjects) != 1:
            return None
        subject = subjects[0]
        if (
            subject.get("kind") == "player"
            and subject.get("state") == "confirmed"
            and subject.get("match_method") == "name_contained"
        ):
            p = next(
                (
                    p
                    for p in players
                    if str(p.get("player_id")) == subject.get("player_id")
                ),
                None,
            )
        else:
            p = conservative_name_match(subjects, players)
        if not p or p.get("online") is False:
            return None
        seat = None
    pid = str(p["player_id"])
    team = _normalize_team(p.get("team"))
    if (
        (pid == incident.get("reporter_id") and not allow_self_reports)
        or team not in {"allies", "axis"}
        or team != _normalize_team(reporter.get("team"))
    ):
        return None
    return {
        "player_id": pid,
        "name": str(p.get("name") or p.get("player_name") or ""),
        "team": team,
        "seat": seat,
    }


def unique_seat(players, seat):
    """A malformed roster must not select between competing leaders."""
    return (
        sum(
            all(other[key] == seat[key] for key in ("team", "kind", "squad_id"))
            for p in players
            if (other := identity(p))
        )
        == 1
    )


def has_role_reference(message, players):
    body = _normalize_message(str(message or ""))
    for p in players:
        name = _normalize_message(str(p.get("name") or p.get("player_name") or ""))
        if name:
            body = re.sub(r"(?<!\w)" + re.escape(name) + r"(?!\w)", " ", body)
    words = set(body.split())
    return bool(
        words.intersection(set(LETTERS) | COMMANDERS | set(SQUAD_TYPOS))
    ) or bool(re.search(r"\b(?:squad|sl|trupp) [a-z]\b", body))


def exact_player(subjects, players):
    if len(subjects) != 1:
        return None
    s = subjects[0]
    if (
        s.get("kind") != "player"
        or s.get("state") != "confirmed"
        or s.get("match_method") != "name_contained"
    ):
        return None
    return next(
        (
            p
            for p in players
            if str(p.get("player_id")) == s.get("player_id")
            and p.get("online") is not False
        ),
        None,
    )


def typo_distance(a, b):
    """Bounded Damerau/OSA distance: insert, delete, replace, transpose."""
    if max(len(a), len(b)) > 100:
        return 101
    table = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        table[i][0] = i
    for j in range(len(b) + 1):
        table[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            table[i][j] = min(
                table[i - 1][j] + 1,
                table[i][j - 1] + 1,
                table[i - 1][j - 1] + (a[i - 1] != b[j - 1]),
            )
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                table[i][j] = min(table[i][j], table[i - 2][j - 2] + 1)
    return table[-1][-1]


def conservative_name_match(subjects, players):
    if len(subjects) != 1:
        return None
    s = subjects[0]
    if (
        s.get("kind") != "player"
        or s.get("state") != "suggested"
        or s.get("match_method") != "fuzzy"
    ):
        return None
    fragment = _normalize_message(str(s.get("matched_text") or ""))
    # Short names and partial names never become an automatic target.
    if len(fragment) < 6:
        return None
    # Include both teams and all plausible names in the collision check.
    ranked = sorted(
        (
            typo_distance(
                fragment,
                _normalize_message(str(p.get("name") or p.get("player_name") or "")),
            ),
            str(p.get("player_id")),
            p,
        )
        for p in players
        if p.get("online") is not False
    )
    if not ranked:
        return None
    distance, pid, player = ranked[0]
    name_length = len(
        _normalize_message(str(player.get("name") or player.get("player_name") or ""))
    )
    allowed = min(3, min(len(fragment), name_length) // 4)
    if (
        distance > allowed
        or pid != str(s.get("player_id"))
        or (len(ranked) > 1 and ranked[1][0] <= distance + 1)
    ):
        return None
    return player
