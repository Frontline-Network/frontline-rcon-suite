from rcon.routines import _next_deadline, _sleep_until_next_deadline


def test_disabled_interval_has_no_deadline():
    assert _next_deadline(0, now=100.0) is None


def test_next_deadline_uses_requested_interval():
    assert _next_deadline(10, now=100.0) == 110.0


def test_sleep_targets_earliest_deadline_and_is_bounded():
    assert _sleep_until_next_deadline(140.0, 110.0, now=100.0) == 10.0
    assert _sleep_until_next_deadline(200.0, now=100.0) == 30.0
    assert _sleep_until_next_deadline(99.0, now=100.0) == 0.1
