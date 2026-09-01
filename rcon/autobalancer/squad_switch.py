from __future__ import annotations


TEAM_NAMES = {"allies", "axis"}
TEAM_LABELS = {"allies": "Alliierte", "axis": "Achsenmächte"}
SPECIAL_SQUAD_TYPES = {
    "armor",
    "armour",
    "recon",
    "artillery",
    "mortar",
    "helicopter",
    "commander",
}


def _normalize(value) -> str:
    return str(value or "").strip().casefold()


def validate_squad_switch_moves(team_view: dict, moves: list[dict]) -> list[dict]:
    """Revalidate a prepared squad action against one fresh live snapshot."""
    if not isinstance(team_view, dict):
        raise ValueError("Live-Spielerdaten haben ein ungültiges Format")
    if team_view.get("fail_count"):
        raise ValueError("Live-Spielerdaten sind derzeit unvollständig")
    if not isinstance(moves, list) or not 1 <= len(moves) <= 2:
        raise ValueError("Ein Auftrag muss einen oder zwei Squad-Wechsel enthalten")

    validated: list[dict] = []
    seen_player_ids: set[str] = set()
    projected_counts = {
        team: int((team_view.get(team) or {}).get("count") or 0)
        for team in TEAM_NAMES
    }
    before_difference = abs(projected_counts["allies"] - projected_counts["axis"])

    for move in moves:
        if not isinstance(move, dict):
            raise ValueError("Ein Squad-Wechsel hat ein ungültiges Format")
        source_team = _normalize(move.get("source_team"))
        target_team = _normalize(move.get("target_team"))
        squad_name = str(move.get("squad_name") or "").strip()
        requested_ids = {
            str(player_id).strip()
            for player_id in (move.get("player_ids") or [])
            if str(player_id).strip()
        }
        if source_team not in TEAM_NAMES or target_team not in TEAM_NAMES:
            raise ValueError("Quell- oder Zielteam ist ungültig")
        if source_team == target_team:
            raise ValueError("Quell- und Zielteam müssen verschieden sein")
        if not squad_name:
            raise ValueError("Der Squad-Name fehlt")

        squads = (team_view.get(source_team) or {}).get("squads") or {}
        matching = next(
            (
                (name, squad)
                for name, squad in squads.items()
                if _normalize(name) == _normalize(squad_name)
            ),
            None,
        )
        if matching is None:
            raise ValueError(
                f"Squad {squad_name} existiert nicht mehr im angegebenen Team"
            )
        current_name, squad = matching
        squad_type = _normalize(squad.get("type"))
        if squad_type in SPECIAL_SQUAD_TYPES:
            raise ValueError(
                f"Squad {current_name} ist ein geschützter Spezial- oder Führungstrupp"
            )
        players = list(squad.get("players") or [])
        if not all(isinstance(player, dict) for player in players):
            raise ValueError(f"Squad {current_name} enthält ungültige Spielerdaten")
        current_ids = {
            str(player.get("player_id") or "").strip()
            for player in players
            if str(player.get("player_id") or "").strip()
        }
        if len(current_ids) < 2:
            raise ValueError(
                f"Squad {current_name} hat nicht genügend Mitglieder für einen Gruppenwechsel"
            )
        if len(current_ids) != len(players):
            raise ValueError(f"Squad {current_name} enthält unvollständige Spieler-IDs")
        if requested_ids != current_ids:
            raise ValueError(f"Squad {current_name} hat sich seit dem Vorschlag verändert")
        if seen_player_ids.intersection(current_ids):
            raise ValueError("Ein Spieler darf nur in einem Squad-Wechsel vorkommen")
        seen_player_ids.update(current_ids)

        projected_counts[source_team] -= len(current_ids)
        projected_counts[target_team] += len(current_ids)
        validated.append(
            {
                "source_team": source_team,
                "target_team": target_team,
                "target_label": TEAM_LABELS[target_team],
                "squad_name": str(current_name),
                "squad_type": squad_type or "unknown",
                "players": [
                    {
                        "player_id": str(player.get("player_id")),
                        "player_name": str(player.get("name") or "Unbekannt"),
                    }
                    for player in players
                ],
            }
        )

    after_difference = abs(projected_counts["allies"] - projected_counts["axis"])
    if after_difference > before_difference:
        raise ValueError("Der Squad-Wechsel würde die Spielerzahl-Balance verschlechtern")
    if before_difference == 0 and after_difference != 0:
        raise ValueError("Ein Stärkeausgleich darf die Spielerzahlen nicht verändern")
    return validated
