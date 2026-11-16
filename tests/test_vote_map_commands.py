"""Command parsing uses synthetic inputs and never reaches a game server."""
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon.vote_map.service import VoteMapCommandHandler


@pytest.fixture
def handler():
    value = VoteMapCommandHandler(None, SimpleNamespace(message_player=Mock()), SimpleNamespace(help_text=None))
    value.handle_vote = Mock()
    value.handle_help = Mock()
    return value


@pytest.mark.parametrize("message,number", [("!vm1", 1), (" !VM  23 ", 23), ("!VoTeMaP 4", 4)])
def test_valid_vote_commands_still_work(handler, message, number):
    log = {"event_time": datetime.now(), "sub_content": message}
    assert handler.execute(log, "fake-id") is True
    handler.handle_vote.assert_called_once_with("fake-id", log, number)


@pytest.mark.parametrize("message", ["!vm 1oops", "!vm 1!", "!vm 1 2", "!votemap 1.0", "!vm 1\n2", "!vm helpx"])
def test_trailing_text_is_rejected_without_recording_vote(handler, message):
    log = {"event_time": datetime.now(), "sub_content": message}
    assert handler.execute(log, "fake-id") is False
    handler.handle_vote.assert_not_called()
    handler.handle_help.assert_not_called()
    assert "INVALID COMMAND" in handler.rcon.message_player.call_args.kwargs["message"]


def test_valid_help_remains_supported(handler):
    log = {"event_time": datetime.now(), "sub_content": "  !VM help  "}
    assert handler.execute(log, "fake-id") is True
    handler.handle_help.assert_called_once_with("fake-id", log)
