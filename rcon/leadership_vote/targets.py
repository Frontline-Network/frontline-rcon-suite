"""Deterministic leadership references, never a best-guess player search.

Normal admin-report parsing is unchanged. These references only offer a private
confirmation; role tenure, sessions, team membership and execution stay in storage.
Alphabet source and the anonymized real-message corpus are in docs/leadership-votes.md.
"""

import re
from collections import defaultdict

from rcon.admin_incidents import (
    _is_commander,
    _is_squad_leader,
    _normalize_message,
    _normalize_team,
)

VERSION = "leadership-targets-1"

# The letter is the bridge, not a numeric RCON unit ID. Both games return the
# actual squad name; a reference must resolve to exactly one existing own-team
# squad. Never choose between two squads that use names for the same letter.
ALPHABET = (
    ("able", "alfa", "alpha"),
    ("baker", "bravo"),
    ("charlie",),
    ("dog", "delta"),
    ("easy", "echo"),
    ("fox", "foxtrot"),
    ("george", "golf"),
    ("how", "hotel"),
    ("item", "india"),
    ("jig", "juliett", "juliet"),
    ("king", "kilo"),
    ("love", "lima"),
    ("mike",),
    ("negat", "nan", "november"),
    ("option", "oboe", "oscar"),
    ("peter", "papa"),
    ("queen", "quebec"),
    ("roger", "romeo"),
    ("sugar", "sierra"),
    ("tare", "tango"),
    ("uncle", "uniform"),
    ("victor",),
    ("william", "whiskey", "whisky"),
    ("xray", "x ray"),
    ("yoke", "yankee"),
    ("zebra", "zulu"),
)
LETTERS = {
    word: chr(ord("a") + index)
    for index, words in enumerate(ALPHABET)
    for word in words
}
# Reviewed misspellings actually found in RCON1-4 reports. No arbitrary fuzzy
# promotion: a new edit-distance neighbor could be another player or squad.
SQUAD_TYPOS = {"eays": "e", "gorge": "g", "geoge": "g"}
COMMANDERS = frozenset(
    {
        "commander",
        "kommandant",
        "kommandeur",
        "cmd",
        "cmdr",
        "cdr",
        "kommi",
        "kommander",
        "komander",
        "comander",
        "kommandar",
        "kommandat",
        "kommder",
    }
)
# Deliberately not "com": "keine com" means communication, not commander.
LEADER_CUES = (
    "sl",
    "squadleader",
    "squadlead",
    "squad leader",
    "squad lead",
    "squadtlead",
    "sqadlead",
    "offi",
    "officer",
    "offizier",
    "truppfuhrer",
    "truppfuhrung",
    "teamleader",
    "team leader",
)
SQUAD_CUES = ("squad", "squads", "sq", "trupp", "unit") + LEADER_CUES
COMPOUND_CUES = ("squad", "sl", "squadlead", "squadleader", "trupp")


def _spans(text, word):
    return [
        m.span() for m in re.finditer(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text)
    ]


def resolve(message, subjects, reporter, players):
    """Return one live player + reference evidence, or None on any ambiguity."""
    prefix = re.match(r"^\s*!admin\b", str(message or ""), re.I)
    team = _normalize_team((reporter or {}).get("team"))
    if not prefix or team not in {"allies", "axis"}:
        return None
    text = _normalize_message(str(message)[prefix.end() : 4000])
    live = [p for p in players if p.get("online") is not False]
    ids = [str(p.get("player_id") or "") for p in live]
    if "" in ids or len(ids) != len(set(ids)):
        return None

    # Full exact names are useful corroboration (squad + its leader) or a real
    # conflict. Ignore shorter names wholly contained in a longer exact name.
    names = []
    for p in live:
        name = _normalize_message(str(p.get("name") or p.get("player_name") or ""))
        if len(name) >= 3:
            names.extend((span, str(p["player_id"])) for span in _spans(text, name))
    names = [
        (span, pid)
        for span, pid in names
        if not any(
            other != span and other[0] <= span[0] and span[1] <= other[1]
            for other, _ in names
        )
    ]

    def inside_name(span):
        return any(
            other != span and other[0] <= span[0] and span[1] <= other[1]
            for other, _ in names
        )

    own = [p for p in live if _normalize_team(p.get("team")) == team]
    seats = defaultdict(list)
    for p in own:
        name = _normalize_message(str(p.get("unit_name") or ""))
        if name and not _is_commander(p):
            seats[(str(p.get("unit_id") or name), name)].append(p)
    by_letter = defaultdict(set)
    by_name = defaultdict(set)
    for seat in seats:
        by_name[seat[1]].add(seat)
        letter = LETTERS.get(seat[1])
        if letter:
            by_letter[letter].add(seat)

    references = []

    def add(form, matches, method):
        for span in _spans(text, form):
            if not inside_name(span):
                references.append((set(matches), {"text": form, "method": method}))

    # Full current names include custom/unknown names. Single letters need an
    # explicit squad/leader cue so English "I" and "a" never choose a squad.
    for name, matches in by_name.items():
        if len(name) > 1:
            add(name, matches, "squad_exact")
    for word, letter in (LETTERS | SQUAD_TYPOS).items():
        matches = by_letter[letter]
        method = "squad_typo" if word in SQUAD_TYPOS else "squad_alphabet"
        add(word, matches, method)
        for cue in COMPOUND_CUES:
            add(word + cue, matches, method)
            add(cue + word, matches, method)
    for letter in "abcdefghijklmnopqrstuvwxyz":
        matches = by_letter[letter] | by_name.get(letter, set())
        for cue in SQUAD_CUES:
            add(cue + " " + letter, matches, "squad_letter")
            add(letter + " " + cue, matches, "squad_letter")

    commanders = [p for p in own if _is_commander(p)]
    commander_refs = []
    for word in COMMANDERS:
        commander_refs.extend(
            word for span in _spans(text, word) if not inside_name(span)
        )

    matched_players = set()
    evidence = []
    for matches, match in references:
        if len(matches) != 1:
            return None  # absent squad or colliding aliases, not a fallback target
        seat = next(iter(matches))
        leaders = [p for p in seats[seat] if _is_squad_leader(p)]
        if len(leaders) != 1:
            return None
        matched_players.add(str(leaders[0]["player_id"]))
        if match not in evidence:
            evidence.append(match)
    if commander_refs:
        # "SL B ... refuses to follow commander" is not a commander report.
        # If the SL reference is unresolved, do not pick the incidental role.
        if not references and any(_spans(text, cue) for cue in LEADER_CUES):
            return None
        if len(commanders) != 1:
            return None
        matched_players.add(str(commanders[0]["player_id"]))
        evidence.extend(
            {"text": word, "method": "commander_alias"}
            for word in sorted(set(commander_refs))
        )

    named_ids = {pid for _, pid in names}
    if not matched_players:
        # A name alone remains an ordinary report. An explicit leadership cue
        # plus one exact current leader name may identify the same safe target.
        if not any(_spans(text, cue) for cue in LEADER_CUES) or len(named_ids) != 1:
            return None
        p = next(p for p in live if str(p["player_id"]) in named_ids)
        if (
            _normalize_team(p.get("team")) != team
            or not _is_squad_leader(p)
            or _is_commander(p)
        ):
            return None
        matched_players.update(named_ids)
        evidence.append(
            {
                "text": str(p.get("name") or p.get("player_name") or ""),
                "method": "leader_name",
            }
        )
    if len(matched_players) != 1 or named_ids - matched_players:
        return None
    target_id = next(iter(matched_players))
    p = next(p for p in own if str(p["player_id"]) == target_id)
    for subject in subjects:
        if subject.get("state") == "rejected":
            return None
        if subject.get("match_method") in {
            "recent_name",
            "recent_teamkill",
            "recent_clan_tag",
        }:
            if str(subject.get("player_id")) != target_id:
                return None  # a departed player cannot silently become a successor
        if subject.get("state") == "confirmed":
            if (
                subject.get("match_method") == "squad_exact"
                and not _is_commander(p)
                and _normalize_message(str(subject.get("squad_name") or ""))
                == _normalize_message(str(p.get("unit_name") or ""))
                and str(subject.get("leader_player_id")) != target_id
            ) or (
                subject.get("match_method") == "team_commander"
                and _is_commander(p)
                and str(subject.get("player_id")) != target_id
            ):
                # The report parser and role snapshot may have been fetched
                # separately. A changed incumbent must not receive the offer.
                return None
    if not _is_commander(p):
        # Also validate name-only resolution and inconsistent snapshots where
        # the same numeric seat is labelled with different squad names.
        seat_id = str(p.get("unit_id") or p.get("unit_name") or "")
        if (
            not p.get("unit_name")
            or not seat_id
            or sum(
                _is_squad_leader(other)
                and not _is_commander(other)
                and str(other.get("unit_id") or other.get("unit_name") or "") == seat_id
                for other in own
            )
            != 1
        ):
            return None
    if named_ids:
        evidence.append(
            {
                "text": str(p.get("name") or p.get("player_name") or ""),
                "method": "exact_player_name",
            }
        )
    return {"player": p, "resolution": {"version": VERSION, "matches": evidence[:20]}}
