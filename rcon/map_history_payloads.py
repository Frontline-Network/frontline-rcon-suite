MAP_HISTORY_SUMMARY_DEFAULT_PAGE_SIZE = 50
MAP_HISTORY_SUMMARY_MAX_PAGE_SIZE = 100


def _positive_int(value, *, name: str, default: int, maximum: int | None = None):
    if value in (None, ""):
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if parsed < 1:
        raise ValueError(f"{name} must be a positive integer")
    if maximum is not None and parsed > maximum:
        raise ValueError(f"{name} must not exceed {maximum}")
    return parsed


def _summary_item(item, *, index: int):
    """Project one map-history item without its large nested match payloads."""

    return {
        "index": index,
        "name": item.get("name"),
        "start": item.get("start"),
        "end": item.get("end"),
        "guessed": bool(item.get("guessed", False)),
        "match_time": item.get("match_time", 0),
    }


def build_map_history_summary(history, *, page=None, limit=None):
    """Build a bounded, game-neutral summary from a Redis-backed map history."""

    parsed_page = _positive_int(page, name="page", default=1)
    page_size = _positive_int(
        limit,
        name="limit",
        default=MAP_HISTORY_SUMMARY_DEFAULT_PAGE_SIZE,
        maximum=MAP_HISTORY_SUMMARY_MAX_PAGE_SIZE,
    )
    total = len(history)
    offset = (parsed_page - 1) * page_size
    items = history[offset : offset + page_size]
    maps = [
        _summary_item(item, index=offset + item_index)
        for item_index, item in enumerate(items)
    ]
    return {
        "page": parsed_page,
        "page_size": page_size,
        "total": total,
        "has_more": offset + len(maps) < total,
        "maps": maps,
    }
