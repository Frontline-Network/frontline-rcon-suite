"""Account-owned live-view display settings; never automation settings."""

from .player_table_preferences import default_player_table, normalize_player_table


def default_user_live_view():
    return {
        "version": 1,
        "players_table": default_player_table(),
        "logs": {"fontSize": "small", "density": "dense"},
        "balance_expanded": True,
        "cards": {
            "commander": False,
            "squad_leaders": False,
            "vips": False,
            "watched": False,
            "score": True,
            "next_map": True,
        },
    }


def normalize_live_view(value):
    allowed = {"version", "cards", "balance_expanded", "players_table", "logs"}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("Expected a live-view preferences object.")
    version = value.get("version", 1)
    if type(version) is not int or version != 1:
        raise ValueError("Unsupported live-view preferences version.")
    result = default_user_live_view()
    logs = value.get("logs", {})
    if not isinstance(logs, dict) or set(logs) - set(result["logs"]):
        raise ValueError("Expected known log-display settings.")
    for key, choices in (
        ("fontSize", ("small", "normal", "large")),
        ("density", ("dense", "normal", "comfortable")),
    ):
        if key in logs:
            if not isinstance(logs[key], str) or logs[key] not in choices:
                raise ValueError(f"Invalid log-display {key}.")
            result["logs"][key] = logs[key]
    result["players_table"] = normalize_player_table(value.get("players_table", {}))
    balance_expanded = value.get("balance_expanded", True)
    if type(balance_expanded) is not bool:
        raise ValueError("Balance detail visibility must be true or false.")
    result["balance_expanded"] = balance_expanded
    cards = value.get("cards", {})
    if not isinstance(cards, dict) or set(cards) - set(result["cards"]):
        raise ValueError("Unknown live-view card.")
    if any(type(enabled) is not bool for enabled in cards.values()):
        raise ValueError("Card visibility must be true or false.")
    result["cards"].update(cards)
    return result
