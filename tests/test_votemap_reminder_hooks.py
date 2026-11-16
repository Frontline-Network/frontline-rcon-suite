"""Match-end reminder scopes use the stable log identity."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon import hooks


@pytest.mark.parametrize("forced", [False, True])
def test_match_end_reminder_uses_event_scope_only_when_forced(monkeypatch, forced):
    vote = Mock()
    vote.enabled = True
    vote.config = SimpleNamespace(remind_on_match_end=forced)
    monkeypatch.setattr(hooks, "VoteMap", lambda: vote)
    hooks.remind_vote_map(None, {"timestamp_ms": 123456, "raw": "synthetic"})
    if forced:
        vote.send_reminder.assert_called_once_with(force=True, scope="event:end:123456")
    else:
        vote.send_reminder.assert_called_once_with(force=False)
    vote.apply_results.assert_called_once()
