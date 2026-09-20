import os
import hllrcon
from datetime import datetime, timedelta, timezone

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.autobalancer.snapshot import build_snapshot
from rcon.game.hllv.profile import HLLV_PROFILE


class Store:
    def track_squad_memberships(self, round_id, memberships, now):
        return {player_id: 600 for player_id in memberships}


class HLLVRcon:
    game_profile = HLLV_PROFILE

    def __init__(self):
        self.compact_team_view_requested = False

    def get_gamestate(self):
        return {
            "current_map": {"id": "wdevc_warfare_day"},
            "num_allied_players": 2,
            "num_axis_players": 0,
            "allied_faction_id": 1,
            "axis_faction_id": 6,
            "time_remaining": timedelta(hours=1),
        }

    def get_raw_player_snapshot(self):
        return {
            "captured_at": datetime(2026, 8, 16, tzinfo=timezone.utc).timestamp(),
            "players": [
                {
                    "iD": "hllv-squad-leader",
                    "name": "Leader",
                    "team": 1,
                    "role": hllrcon.HLLVRole.SQUAD_LEADER.id,
                    "platoon": "Able",
                },
                {
                    "iD": "hllv-mortar-gunner",
                    "name": "Gunner",
                    "team": 1,
                    "role": 15,
                    "platoon": "Baker",
                },
            ],
        }

    def get_team_view(self, compact=False):
        raise AssertionError("The cached UI roster must not drive automatic balancing")

    def get_autobalance_enabled(self):
        return True

    def get_autobalance_threshold(self):
        return 2


def test_hllv_snapshot_uses_game_roles_and_faction_labels(monkeypatch):
    monkeypatch.setattr(
        "rcon.autobalancer.snapshot.time.time",
        lambda: datetime(2026, 8, 16, tzinfo=timezone.utc).timestamp(),
    )
    monkeypatch.setattr(
        "rcon.autobalancer.snapshot.get_live_profiles",
        lambda ids: [
            {"player_id": pid, "current_playtime_seconds": 900} for pid in ids
        ],
    )
    monkeypatch.setattr(
        "rcon.autobalancer.snapshot._current_round",
        lambda map_name, now: ("1000:wdevc_warfare_day", 900, True),
    )

    rcon = HLLVRcon()
    snapshot = build_snapshot(
        rcon,
        Store(),
        now=datetime(2026, 8, 16, tzinfo=timezone.utc),
    )

    assert rcon.compact_team_view_requested is False
    assert snapshot.team_labels == {"allies": "US", "axis": "NVA"}
    assert snapshot.game == "hllv"
    assert snapshot.counts_match is True
    players = {player.player_id: player for player in snapshot.players}
    assert players["hllv-squad-leader"].is_leader is True
    assert players["hllv-mortar-gunner"].unit_type == "mortar"
