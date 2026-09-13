"""Validated account-owned presentation settings, never table data or filters."""

PLAYER_COLUMN_IDS = (
    "select", "details", "player_summary", "team", "unit", "role", "level",
    "platform", "clan-tag", "name", "player_id", "country", "kills", "deaths",
    "kpm", "team_kills", "combat", "offense", "defense", "support",
    "vehicle_kills", "vehicles_destroyed", "performance_summary", "status_summary",
    "active_ban", "warnings", "watchlist", "vip", "flags", "visits", "time", "actions",
)
FIXED_PLAYER_COLUMNS = {"select", "details", "player_summary", "actions"}
OPERATIONS_COLUMNS = FIXED_PLAYER_COLUMNS | {
    "team", "unit", "kills", "deaths", "team_kills", "status_summary", "time",
}


def default_player_table():
    return {
        "preset": "operations", "fontSize": "small", "density": "dense",
        "columnVisibility": {key: key in OPERATIONS_COLUMNS for key in PLAYER_COLUMN_IDS},
    }


def normalize_player_table(value):
    result = default_player_table()
    if not isinstance(value, dict) or set(value) - set(result):
        raise ValueError("Expected known player-table settings.")
    for key, allowed in (
        ("preset", ("operations", "all", "custom")),
        ("fontSize", ("small", "normal", "large")),
        ("density", ("dense", "normal", "comfortable")),
    ):
        if key in value:
            if not isinstance(value[key], str) or value[key] not in allowed:
                raise ValueError(f"Invalid player-table {key}.")
            result[key] = value[key]
    columns = value.get("columnVisibility", {})
    if not isinstance(columns, dict) or set(columns) - set(PLAYER_COLUMN_IDS):
        raise ValueError("Unknown player-table column.")
    if any(type(visible) is not bool for visible in columns.values()):
        raise ValueError("Column visibility must be true or false.")
    result["columnVisibility"].update(columns)
    for key in FIXED_PLAYER_COLUMNS:
        result["columnVisibility"][key] = True
    return result
