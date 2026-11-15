from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon.vote_map.service import VoteMap
from rcon.commands import HLLCommandFailedError


def test_rejected_votemap_winner_preserves_old_entries():
    old = [SimpleNamespace(id="old_a"), SimpleNamespace(id="old_b")]
    winner = SimpleNamespace(id="winner")
    rcon = Mock()
    rcon.get_map_rotation.return_value = {"maps": old}
    rcon.add_map_to_rotation.side_effect = RuntimeError("rejected")
    vote = SimpleNamespace(_rcon=rcon, generate_next_map=Mock(return_value=winner))

    with pytest.raises(HLLCommandFailedError, match="observed after failure"):
        VoteMap.apply_results.__wrapped__(vote)

    rcon.remove_map_from_rotation.assert_not_called()


@pytest.mark.parametrize("phase", ["add", "remove"])
def test_votemap_lost_reply_reports_observed_rotation_without_replaying(phase):
    old = [SimpleNamespace(id="old_a"), SimpleNamespace(id="old_b")]
    winner = SimpleNamespace(id="winner")
    state = list(old)
    rcon = Mock()
    rcon.get_map_rotation.side_effect = lambda: {"maps": list(state)}

    def add(_):
        state.append(winner)
        if phase == "add":
            raise TimeoutError("reply lost")

    def remove(map_id):
        state[:] = [item for item in state if item.id != map_id]
        raise TimeoutError("reply lost")

    rcon.add_map_to_rotation.side_effect = add
    rcon.remove_map_from_rotation.side_effect = remove
    vote = SimpleNamespace(_rcon=rcon, generate_next_map=Mock(return_value=winner))
    with pytest.raises(HLLCommandFailedError) as exc:
        VoteMap.apply_results.__wrapped__(vote)
    assert f"observed after failure: {[item.id for item in state]!r}" in str(exc.value)
    assert rcon.add_map_to_rotation.call_count == 1
    assert rcon.remove_map_from_rotation.call_count == (1 if phase == "remove" else 0)


def test_existing_votemap_winner_is_kept():
    old = SimpleNamespace(id="old")
    winner = SimpleNamespace(id="winner")
    rcon = Mock()
    rcon.get_map_rotation.side_effect = [{"maps": [old, winner]}, {"maps": [winner]}]
    vote = SimpleNamespace(_rcon=rcon, generate_next_map=Mock(return_value=winner), set_next_map=Mock())

    assert VoteMap.apply_results.__wrapped__(vote) == winner
    rcon.add_map_to_rotation.assert_not_called()
    rcon.remove_map_from_rotation.assert_called_once_with("old")


def test_votemap_does_not_replay_if_verification_shows_an_unexpected_rotation():
    old = SimpleNamespace(id="old")
    winner = SimpleNamespace(id="winner")
    rcon = Mock()
    rcon.get_map_rotation.side_effect = [{"maps": [old]}, {"maps": [old, winner]}]
    vote = SimpleNamespace(_rcon=rcon, generate_next_map=Mock(return_value=winner), set_next_map=Mock())

    assert VoteMap.apply_results.__wrapped__(vote) is None
    rcon.add_map_to_rotation.assert_called_once_with("winner")
    rcon.remove_map_from_rotation.assert_called_once_with("old")
    vote.set_next_map.assert_not_called()


def test_votemap_reports_failure_if_verification_is_unavailable():
    old = SimpleNamespace(id="old")
    winner = SimpleNamespace(id="winner")
    rcon = Mock()
    rcon.get_map_rotation.side_effect = [{"maps": [old]}, OSError("disconnected"), OSError("still disconnected")]
    vote = SimpleNamespace(_rcon=rcon, generate_next_map=Mock(return_value=winner), set_next_map=Mock())

    with pytest.raises(HLLCommandFailedError, match="observed after failure: unavailable"):
        VoteMap.apply_results.__wrapped__(vote)
    rcon.add_map_to_rotation.assert_called_once_with("winner")
    rcon.remove_map_from_rotation.assert_called_once_with("old")
    vote.set_next_map.assert_not_called()
