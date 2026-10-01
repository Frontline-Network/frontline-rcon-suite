from rcon.routines import _next_deadline, _sleep_until_next_deadline


def test_disabled_interval_has_no_deadline():
    assert _next_deadline(0, now=100.0) is None


def test_next_deadline_uses_requested_interval():
    assert _next_deadline(10, now=100.0) == 110.0


def test_sleep_targets_earliest_deadline_and_is_bounded():
    assert _sleep_until_next_deadline(140.0, 110.0, now=100.0) == 10.0
    assert _sleep_until_next_deadline(200.0, now=100.0) == 30.0
    assert _sleep_until_next_deadline(99.0, now=100.0) == 0.1


def test_queue_failure_does_not_stop_other_routines(monkeypatch):
    from unittest.mock import Mock
    from rcon import routines
    from rcon.leadership_vote import service

    stop = Mock()
    stop.is_set.side_effect = [False, True]
    api = Mock()
    api.performance_stats_interval.return_value = 0
    watchdog = Mock()
    watchdog.step.side_effect = RuntimeError("queue observation failed")
    leadership = Mock()
    vote_map = Mock()
    monkeypatch.setattr(routines, "get_rcon", lambda: api)
    monkeypatch.setattr(routines, "QueueWatchdog", lambda: watchdog)
    monkeypatch.setattr(service, "Runtime", lambda: leadership)
    monkeypatch.setattr(routines, "VoteMap", lambda: vote_map)
    toggle = Mock()
    monkeypatch.setattr(routines, "toggle_votekick", toggle)
    routines.run(stop)
    watchdog.step.assert_called_once_with(api)
    watchdog.detector.reset.assert_called_once()
    leadership.step.assert_called_once_with(api)
    leadership.close.assert_called_once()
    toggle.assert_called_once_with(api)
    vote_map.send_reminder.assert_called_once()
