import json
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon import queue_watchdog as q


def sample(now=0, **changes):
    return replace(
        q.Sample(
            10000 + now,
            "map:1",
            1000 + now,
            5000 - now,
            frozenset({"p1", "p2"}),
            100,
            6,
            6,
            2,
        ),
        **changes,
    )


def observe(detector, now, **changes):
    return detector.observe(sample(now, **changes), now=now, wall_time=10000 + now)


def blocked(detector, start=0):
    result = None
    for now in range(start, start + 181, 30):
        result = observe(detector, now)
    return result


def test_requires_three_minutes_of_continuous_evidence():
    detector = q.Detector()
    for now in range(0, 180, 30):
        assert observe(detector, now)["alert"] is False
    result = observe(detector, 180)
    assert result["alert"] is True
    assert result["observed_seconds"] == 180
    detector.reported = True
    assert observe(detector, 210)["alert"] is False


@pytest.mark.parametrize(
    "changes",
    [
        {"queued": 0},
        {"player_ids": frozenset(str(i) for i in range(98))},
        {"player_ids": frozenset(str(i) for i in range(97))},
        {"round_age": 0},
        {"round_age": 179},
    ],
)
def test_empty_queue_reserved_capacity_and_round_grace_never_alert(changes):
    detector = q.Detector()
    for now in range(0, 400, 30):
        assert observe(detector, now, **changes)["alert"] is False


def test_same_count_with_replacement_player_is_progress():
    detector = q.Detector()
    for now in range(0, 180, 30):
        observe(detector, now)
    result = observe(detector, 180, player_ids=frozenset({"p2", "new"}))
    assert result["observed_seconds"] == 0
    assert result["alert"] is False


def test_departures_alone_do_not_clear_a_stall():
    detector = q.Detector()
    for now in range(0, 180, 30):
        observe(detector, now)
    assert observe(detector, 180, player_ids=frozenset({"p2"}))["alert"] is True


@pytest.mark.parametrize("changes", [{"round_id": "map:2"}, {"remaining": 5400}])
def test_new_round_or_timer_reset_has_a_fresh_grace(changes):
    detector = q.Detector()
    blocked(detector)
    result = observe(detector, 210, **changes)
    assert result["state"] == "round_grace"
    assert result["alert"] is False


@pytest.mark.parametrize(
    "changes", [{"vip_slots": 3}, {"capacity": 99}, {"queue_limit": 7}]
)
def test_changing_slot_limits_resets_evidence(changes):
    detector = q.Detector()
    blocked(detector)
    result = observe(detector, 210, **changes)
    assert result["alert"] is False
    assert result["observed_seconds"] == 0


def test_gaps_and_backwards_monotonic_time_reset_evidence():
    detector = q.Detector()
    blocked(detector)
    assert observe(detector, 300)["observed_seconds"] == 0
    assert observe(detector, 299)["observed_seconds"] == 0


@pytest.mark.parametrize("age", [-1, 11, float("nan")])
def test_stale_or_future_samples_cannot_warn(age):
    detector = q.Detector()
    blocked(detector)
    assert detector.observe(sample(210), now=210, wall_time=10210 + age) == {
        "state": "unknown",
        "alert": False,
    }
    assert detector.since is None


@pytest.fixture
def capture_setup(monkeypatch):
    history = {"name": "map", "start": 9000, "end": None, "guessed": False}
    history_reader = Mock(return_value=history)
    monkeypatch.setattr(
        "rcon.utils.MapsHistory",
        lambda: SimpleNamespace(get_current_map=history_reader),
    )
    monkeypatch.setattr(q.time, "time", lambda: 10000)
    session = {
        "mapId": "map",
        "maxPlayerCount": 100,
        "playerCount": 2,
        "queueCount": 6,
        "maxQueueCount": 6,
        "maxVipQueueCount": 2,
        "vipQueueCount": 62,
        "remainingMatchTime": 5000,
    }
    rows = [{"iD": "one"}, {"iD": "two"}]
    api = Mock()
    api.exchange.side_effect = lambda command, version, body: SimpleNamespace(
        content_dict=session if body["Name"] == "session" else {"players": rows}
    )
    return api, session, rows, history, history_reader


def test_capture_is_read_only_and_ignores_unreliable_vip_queue_count(capture_setup):
    api, *_ = capture_setup
    result = q.capture(api)
    assert result.queued == 6
    assert result.public_free == 96
    assert [c.args for c in api.exchange.call_args_list] == [
        ("GetServerInformation", 2, {"Name": "session", "Value": ""}),
        ("GetServerInformation", 2, {"Name": "players", "Value": ""}),
    ]
    assert len(api.mock_calls) == 2


@pytest.mark.parametrize(
    "key,value",
    [
        ("queueCount", 7),
        ("queueCount", -1),
        ("queueCount", True),
        ("queueCount", "6"),
        ("maxQueueCount", None),
        ("maxVipQueueCount", 101),
        ("maxPlayerCount", 0),
        ("playerCount", 3),
        ("remainingMatchTime", -1),
        ("mapId", "other"),
    ],
)
def test_invalid_or_incoherent_counts_reset_capture(capture_setup, key, value):
    api, session, *_ = capture_setup
    session[key] = value
    with pytest.raises(ValueError):
        q.capture(api)


@pytest.mark.parametrize(
    "change",
    [
        {"end": 9999},
        {"start": None},
        {"start": 10001},
        {"start": float("nan")},
        {"guessed": True},
    ],
)
def test_unconfirmed_or_ended_round_is_not_evidence(capture_setup, change):
    api, _, _, history, _ = capture_setup
    history.update(change)
    with pytest.raises(ValueError):
        q.capture(api)


def test_round_change_during_capture_is_rejected(capture_setup):
    api, _, _, history, history_reader = capture_setup
    history_reader.side_effect = [history, {**history, "start": 9999}]
    with pytest.raises(ValueError):
        q.capture(api)


@pytest.mark.parametrize("row", [{"iD": "one"}, {"iD": ""}, {"iD": 123}, {}])
def test_duplicate_or_missing_roster_ids_are_rejected(capture_setup, row):
    api, _, rows, *_ = capture_setup
    rows[1] = row
    with pytest.raises(ValueError):
        q.capture(api)


def test_slow_sample_is_rejected(capture_setup, monkeypatch):
    monkeypatch.setattr(q.time, "time", Mock(side_effect=[10000, 10011]))
    with pytest.raises(ValueError):
        q.capture(capture_setup[0])


@pytest.fixture
def runtime(monkeypatch):
    red, notify, api = Mock(), Mock(), Mock()
    red.set.return_value = True
    monkeypatch.setenv("HLL_QUEUE_WATCHDOG_ENABLED", "true")
    monkeypatch.setattr("rcon.cache_utils.get_redis_client", lambda: red)
    monkeypatch.setattr("rcon.utils.get_server_number", lambda: "3")
    monkeypatch.setattr("rcon.discord.send_to_discord_audit", notify)
    watchdog = q.QueueWatchdog()

    def step(now):
        monkeypatch.setattr(q, "capture", lambda _: sample(now))
        monkeypatch.setattr(q.time, "time", lambda: 10000 + now)
        monkeypatch.setattr(q.time, "monotonic", lambda: now)
        watchdog.step(api)

    return watchdog, red, notify, api, step


def test_alert_is_admin_only_once_per_episode_and_status_has_no_ids(runtime):
    watchdog, red, notify, api, step = runtime
    for now in range(0, 391, 30):
        step(now)
    notify.assert_called_once()
    assert "no automatic action" in notify.call_args.args[0].lower()
    assert "kein automatischer Eingriff" in notify.call_args.args[0]
    red.set.assert_called_once_with(
        "queue_watchdog:3:alert_cooldown", "1", nx=True, ex=900
    )
    status = json.loads(red.setex.call_args.args[2])
    assert status["state"] == "suspected_stall"
    assert "player_ids" not in status
    assert api.mock_calls == []


def test_cooldown_survives_new_detector_and_is_server_scoped(runtime, monkeypatch):
    _, red, notify, _, step = runtime
    red.set.return_value = False
    for now in range(0, 181, 30):
        step(now)
    notify.assert_not_called()
    monkeypatch.setattr("rcon.utils.get_server_number", lambda: "4")
    red.set.return_value = True
    step(210)
    assert red.set.call_args.args[0] == "queue_watchdog:4:alert_cooldown"
    notify.assert_called_once()


def test_uncertain_notification_is_not_automatically_resent(runtime):
    _, _, notify, _, step = runtime
    notify.side_effect = TimeoutError("unknown delivery")
    for now in range(0, 180, 30):
        step(now)
    with pytest.raises(TimeoutError):
        step(180)
    step(210)
    assert notify.call_count == 1


def test_bad_data_clears_evidence_and_never_sends(runtime, monkeypatch):
    watchdog, _, notify, api, step = runtime
    for now in range(0, 180, 30):
        step(now)
    monkeypatch.setattr(q, "capture", Mock(side_effect=ValueError("bad sample")))
    watchdog.step(api)
    assert watchdog.detector.since is None
    notify.assert_not_called()


def test_disabled_watchdog_makes_no_calls(runtime, monkeypatch):
    watchdog, red, notify, api, step = runtime
    monkeypatch.setenv("HLL_QUEUE_WATCHDOG_ENABLED", "false")
    step(0)
    assert red.mock_calls == api.mock_calls == notify.mock_calls == []
