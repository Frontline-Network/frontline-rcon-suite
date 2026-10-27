"""Conservative report classification; text is data, never an instruction.

Unsupported wording is a manual report, not a
best-guess sanction. Communication is a reported allegation, not voice evidence.
"""

import re

from rcon.admin_incidents import _normalize_message, _normalize_team
from rcon.leadership_vote.domain import identity, may_report
from rcon.leadership_vote.targets import resolve, LETTERS, COMMANDERS, SQUAD_TYPOS

MAX_REPORT_AGE = 60

COMMUNICATION = re.compile(
    r"\b(?:redet nicht|spricht nicht|kommuniziert nicht|keine? (?:komms?|com{1,2}s?|kommunikation|voip)|"
    r"not (?:talking|communicating|speaking)|does not (?:talk|communicate|speak)|"
    r"no (?:com{1,2}s?|communication|voip)|doesn t (?:talk|communicate|speak))\b"
)
# A return-to-server aside does not retract a communication complaint. Match
# only this complete parenthetical statement; never discard arbitrary asides
# (which may contain a correction, negation, different target or accusation).
RETURN_TO_SERVER_ASIDE = re.compile(
    r"\(\s*(?:ist (?:schon )?wieder auf dem server|"
    r"is (?:already )?back on the server)\s*\)",
    re.I,
)
TEAMKILLS = re.compile(
    r"\b(?:teamkills?|teamkillt|teamkilling|teamkiller|tk|tks|tk[st]|team killed|team killing)\b"
)
CHEATING = re.compile(r"\b(?:cheat\w*|hack\w*|aimbot|wallhack)\b")
# A mixed/qualified complaint is deliberately not sufficient for direct action.
QUALIFIED = re.compile(
    r"\b(?:nicht mehr|doch|wieder|aber|vielleicht|angeblich|sagt|sagte|behauptet|"
    r"kein teamkill\w*|keine teamkills|nicht teamkill\w*|kein tk|keine tks|nicht kicken|"
    r"not anymore|anymore|but|maybe|says|said|claims|accident|accidental|"
    r"stimmt nicht|nicht wahr|not true|false report|falschmeldung|"
    r"nicht (?:stumm|sprachlos)|not (?:silent|mute)|"
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
    text = _normalize_message(RETURN_TO_SERVER_ASIDE.sub(" ", raw))
    # A player's name must not manufacture a complaint (e.g. "No Comms").
    for p in sorted(players, key=lambda p: len(str(p.get("name") or "")), reverse=True):
        name = _normalize_message(str(p.get("name") or p.get("player_name") or ""))
        if name:
            text = re.sub(r"(?<!\w)" + re.escape(name) + r"(?!\w)", " ", text)
    # Cheat reviews can accept suspicions, but never a mixed actionable rule.
    # They are evidence summaries for humans, with no automatic sanction path.
    if CHEATING.search(text):
        return (
            "cheating"
            if not COMMUNICATION.search(text) and not TEAMKILLS.search(text)
            else None
        )
    # Teamkill complaints are allegations. Even qualified/accidental cases may
    # be reviewed; the complaint itself never supplies evidence of intent.
    if TEAMKILLS.search(text) and not COMMUNICATION.search(text):
        return "teamkills"
    if QUALIFIED.search(text) or any(c in text for c in ('"', "?", "“", "”")):
        return None
    comm, tk = bool(COMMUNICATION.search(text)), bool(TEAMKILLS.search(text))
    if comm == tk:
        return None
    return "communication" if comm else "teamkills"


def communication_identity(player, allow_members=False):
    """Bind named members to their own seat without changing leadership rules."""
    if not player or player.get("online") is False:
        return None
    if seat := identity(player):
        return seat
    team = _normalize_team(player.get("team"))
    squad = str(player.get("unit_name") or "").strip()
    role = re.sub(r"[^a-z0-9]", "", str(player.get("role") or "").casefold())
    if (
        not allow_members
        or not player.get("player_id")
        or team not in {"allies", "axis"}
        or squad.casefold() in {"", "unassigned", "command", "none", "unset"}
        or role in {"", "unassigned", "unknown", "none", "unset"}
    ):
        return None
    unit_id = player.get("unit_id")
    return {
        "team": team,
        "role": role,
        "kind": "squadmember",
        "squad": squad,
        "squad_id": str(unit_id if unit_id is not None else squad),
        "player_id": str(player["player_id"]),
    }


def unique_communication_seat(players, seat):
    if seat.get("kind") != "squadmember":
        return unique_seat(players, seat)
    return sum(communication_identity(p, True) == seat for p in players) == 1


def target_for(
    incident,
    players,
    rule,
    *,
    allow_self_reports=False,
    communication_squad_members=False,
):
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
            or (
                s.get("player_id")
                and str(s["player_id"]) != str(p["player_id"])
                and not (found and _same_squad_word_fuzzy_suggestion(s, found))
            )
            for s in incident.get("subjects", [])
        ):
            return None
        # A member is eligible only through an independently resolved player
        # name, never by relaxing the squad/commander resolver.
        seat = communication_identity(p, communication_squad_members and not found)
        if seat and seat["kind"] == "squadmember":
            fragment = _normalize_message(
                str((incident.get("subjects") or [{}])[0].get("matched_text") or "")
            )
            if fragment in {
                _normalize_message(str(q.get("unit_name") or "")) for q in players
            } | set(LETTERS) | COMMANDERS | set(SQUAD_TYPOS):
                return None  # A player/squad name collision is not a member report.
        if (
            not seat
            or not unique_communication_seat(players, seat)
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
        or _normalize_team(reporter.get("team")) not in {"allies", "axis"}
        or (rule != "cheating" and team != _normalize_team(reporter.get("team")))
    ):
        return None
    return {
        "player_id": pid,
        "name": str(p.get("name") or p.get("player_name") or ""),
        "team": team,
        "seat": seat,
    }


def _same_squad_word_fuzzy_suggestion(subject, resolved):
    """Ignore only a fuzzy player guess for an independently resolved squad word.

    The resolver has already rejected exact player-name collisions, absent or
    ambiguous squads and competing leaders. Other fragments, confirmed targets,
    recent-player references and explicit rejections remain authoritative.
    """
    if (
        subject.get("kind") != "player"
        or subject.get("state") != "suggested"
        or subject.get("match_method") != "fuzzy"
    ):
        return False
    fragment = _normalize_message(str(subject.get("matched_text") or ""))
    return bool(fragment) and any(
        match.get("method")
        in {"squad_exact", "squad_alphabet", "squad_letter", "squad_typo"}
        and fragment == _normalize_message(str(match.get("text") or ""))
        for match in resolved["resolution"]["matches"]
    )


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


def _name_match_score(fragment, name):
    """Compare full names and distinctive prefixes ending at a separator.

    Keep competing prefixes in the ranking even when they exceed their own
    one-typo budget: they can still make another candidate ambiguous.
    """
    if max(len(fragment), len(name)) > 100:
        return 101, 0
    options = [
        (typo_distance(fragment, name), min(3, min(len(fragment), len(name)) // 4))
    ]
    if sum(char.isalnum() for char in fragment) >= 6:
        for end, char in enumerate(name):
            if char not in {"_", " "}:
                continue
            prefix = name[:end]
            if sum(char.isalnum() for char in prefix) >= 6 and any(
                char.isalnum() for char in name[end + 1 :]
            ):
                options.append((typo_distance(fragment, prefix), 1))
    # Prefer the full-name budget when both comparisons have the same distance.
    return min(options, key=lambda option: (option[0], -option[1]))


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
    # Short references remain manual, including short fragments of long names.
    if len(fragment) < 6:
        return None
    # Include both teams and all plausible names in the collision check.
    ranked = []
    for player in players:
        if player.get("online") is False:
            continue
        name = _normalize_message(
            str(player.get("name") or player.get("player_name") or "")
        )
        distance, allowed = _name_match_score(fragment, name)
        ranked.append((distance, str(player.get("player_id")), player, allowed))
    ranked.sort(key=lambda candidate: (candidate[0], candidate[1]))
    if not ranked:
        return None
    distance, pid, player, allowed = ranked[0]
    if (
        distance > allowed
        or pid != str(s.get("player_id"))
        or (len(ranked) > 1 and ranked[1][0] <= distance + 1)
    ):
        return None
    return player
