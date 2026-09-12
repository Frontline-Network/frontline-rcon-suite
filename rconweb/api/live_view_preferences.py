"""Account-owned live-view display settings; never automation settings."""


def default_user_live_view():
    return {
        "version": 1,
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
    if not isinstance(value, dict) or set(value) - {"version", "cards"}:
        raise ValueError("Expected a live-view preferences object.")
    version = value.get("version", 1)
    if type(version) is not int or version != 1:
        raise ValueError("Unsupported live-view preferences version.")
    result = default_user_live_view()
    cards = value.get("cards", {})
    if not isinstance(cards, dict) or set(cards) - set(result["cards"]):
        raise ValueError("Unknown live-view card.")
    if any(type(enabled) is not bool for enabled in cards.values()):
        raise ValueError("Card visibility must be true or false.")
    result["cards"].update(cards)
    return result
