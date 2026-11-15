from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon.vote_map.service import VoteMap


def test_rejected_votemap_winner_preserves_old_entries():
    old = [SimpleNamespace(id="old_a"), SimpleNamespace(id="old_b")]
    winner = SimpleNamespace(id="winner")
    rcon = Mock()
    rcon.get_map_rotation.return_value = {"maps": old}
    rcon.add_map_to_rotation.side_effect = RuntimeError("rejected")
    vote = SimpleNamespace(_rcon=rcon, generate_next_map=Mock(return_value=winner))

    with pytest.raises(RuntimeError, match="rejected"):
        VoteMap.apply_results.__wrapped__(vote)

    rcon.remove_map_from_rotation.assert_not_called()


def test_existing_votemap_winner_is_kept():
    old = SimpleNamespace(id="old")
    winner = SimpleNamespace(id="winner")
    rcon = Mock()
    rcon.get_map_rotation.side_effect = [{"maps": [old, winner]}, {"maps": [winner]}]
    vote = SimpleNamespace(_rcon=rcon, generate_next_map=Mock(return_value=winner), set_next_map=Mock())

    assert VoteMap.apply_results.__wrapped__(vote) == winner
    rcon.add_map_to_rotation.assert_not_called()
    rcon.remove_map_from_rotation.assert_called_once_with("old")
