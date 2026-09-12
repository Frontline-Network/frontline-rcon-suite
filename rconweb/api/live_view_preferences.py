"""Account-owned live-view display settings; never automation settings."""


def default_user_live_view():
    return {
        "version": 1,
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
    if not isinstance(value, dict) or set(value) - {"version", "cards", "balance_expanded"}:
        raise ValueError("Expected a live-view preferences object.")
    version = value.get("version", 1)
    if type(version) is not int or version != 1:
        raise ValueError("Unsupported live-view preferences version.")
    result = default_user_live_view()
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
