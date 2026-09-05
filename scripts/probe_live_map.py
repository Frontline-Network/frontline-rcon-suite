"""Read-only capability probe. Prints shapes and anonymous coordinates, never identities."""
import json
import time

from rcon.rcon import get_rcon


def main():
    api = get_rcon()
    start = time.monotonic()
    raw = api.exchange("GetServerInformation", 2, {"Name": "players", "Value": ""}).content_dict
    players = raw.get("players", [])
    vectors = [p.get("worldPosition", p.get("WorldPosition")) for p in players]
    state = api.get_gamestate()
    print(json.dumps({
        "game": api.config.game.value,
        "count": len(players),
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "player_fields": sorted({k for p in players for k in p}),
        "position_count": sum(isinstance(v, dict) for v in vectors),
        "anonymous_position_examples": vectors[:3],
        "map": state.get("current_map"),
    }, default=str, ensure_ascii=True))
    try:
        commands = api.exchange("GetDisplayableCommands", 2).content_dict
        names = [c.get("iD", c.get("Id")) for c in commands.get("entries", [])]
        print(json.dumps({"command_count": len(names), "object_commands": [n for n in names if any(s in str(n).lower() for s in ("garrison", "outpost", "spawn", "deploy", "position"))]}, ensure_ascii=True))
    except Exception as exc:
        print(json.dumps({"command_probe_error_type": type(exc).__name__}))


if __name__ == "__main__":
    main()
