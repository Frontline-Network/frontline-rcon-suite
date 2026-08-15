from unittest.mock import MagicMock, patch

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from rcon.models import PlayerID
from rcon.player_history import _save_player_id
from rcon.workers import _build_player_stat_dict


def test_player_stats_use_zero_when_live_level_is_missing():
    stats = _build_player_stat_dict(
        player_id_id=1,
        map_id=2,
        game_log_stats={"player": "UnknownLevel"},
        temp_stats={"level": None},
    )

    assert stats["level"] == 0


def test_concurrent_player_insert_recovers_existing_record():
    session = MagicMock(spec=Session)
    session.flush.side_effect = IntegrityError(
        "INSERT INTO steam_id_64", {}, Exception("duplicate key")
    )
    existing = PlayerID(player_id="shared-player-id")

    with patch(
        "rcon.player_history.get_player", side_effect=[None, existing]
    ) as get_player:
        result = _save_player_id(session, "shared-player-id")

    assert result is existing
    assert get_player.call_count == 2
    session.commit.assert_not_called()
