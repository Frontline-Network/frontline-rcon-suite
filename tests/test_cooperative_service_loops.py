from contextlib import nullcontext
from unittest import mock

from rcon import auto_settings, broadcast, campaign_delivery, scoreboard, watch_killrate
from rcon.automods import automod
from rcon.logs.loop import LogLoop
from rcon.logs.stream import LogStream
from rcon.seed_vip import service as seed_vip
from rcon.vip_rewards import service as vip_rewards


class StopAfterFirstWait:
    def __init__(self):
        self.stopped = False
        self.waits = []

    def is_set(self):
        return self.stopped

    def wait(self, seconds):
        self.waits.append(seconds)
        self.stopped = True
        return True


def test_auto_settings_loop_stops_cooperatively():
    stop_event = StopAfterFirstWait()
    config = {
        "always_apply_defaults": False,
        "can_invoke_multiple_rules": False,
        "defaults": {},
        "rules": [],
    }

    with (
        mock.patch.object(auto_settings, "get_rcon_api", return_value=mock.Mock()),
        mock.patch.object(
            auto_settings.AutoSettingsConfig,
            "get_settings",
            return_value=config,
        ),
        mock.patch.object(auto_settings, "do_run_commands") as run_commands,
    ):
        auto_settings.run(stop_event=stop_event)

    assert stop_event.waits == [60]
    run_commands.assert_called_once_with(mock.ANY, {})


def test_broadcast_loop_stops_cooperatively_when_disabled():
    stop_event = StopAfterFirstWait()
    disabled_config = mock.Mock(enabled=False, messages=[])

    with (
        mock.patch("rcon.rcon.get_rcon", return_value=mock.Mock()),
        mock.patch.object(
            broadcast.AutoBroadcastUserConfig,
            "load_from_db",
            return_value=disabled_config,
        ),
    ):
        broadcast.run(stop_event=stop_event)

    assert stop_event.waits == [broadcast.CHECK_INTERVAL]


def test_campaign_loop_stops_cooperatively_when_disabled():
    stop_event = StopAfterFirstWait()
    config = mock.Mock(enabled=False)

    with (
        mock.patch("rcon.rcon.get_rcon", return_value=mock.Mock()),
        mock.patch.object(campaign_delivery, "_recover_interrupted_deliveries"),
        mock.patch.object(campaign_delivery, "_all_direct_campaigns", return_value=[]),
        mock.patch.object(campaign_delivery, "_direct_campaigns", return_value=[]),
        mock.patch.object(
            campaign_delivery.AutoBroadcastUserConfig,
            "load_from_db",
            return_value=config,
        ),
        mock.patch("rcon.vip_lifecycle.feature_enabled", return_value=False),
    ):
        campaign_delivery.run(stop_event=stop_event)

    assert stop_event.waits == [campaign_delivery.CHECK_INTERVAL]


def test_log_event_loop_stops_cooperatively():
    stop_event = StopAfterFirstWait()
    loop = object.__new__(LogLoop)
    loop.now = 0

    with (
        mock.patch("rcon.logs.loop.load_generic_hooks"),
        mock.patch.object(loop, "process_logs"),
        mock.patch.object(loop, "update_maps_history", return_value=0),
        mock.patch.object(loop, "cleanup", side_effect=lambda value, _minutes: value),
    ):
        loop.run(stop_event=stop_event)

    assert stop_event.waits == [2]


def test_log_stream_stops_cooperatively():
    stop_event = StopAfterFirstWait()
    stream = object.__new__(LogStream)
    stream.rcon = mock.Mock()
    stream.rcon.get_structured_logs.return_value = {"logs": []}
    stream.log_stream = mock.Mock()
    stream.log_stream.tail.return_value = None
    config = mock.Mock(
        startup_since_mins=5,
        refresh_since_mins=1,
        refresh_frequency_sec=2,
        enabled=True,
    )

    with (
        mock.patch(
            "rcon.logs.stream.LogStreamUserConfig.load_from_db",
            return_value=config,
        ),
        mock.patch.object(stream, "_append_new_logs", return_value=(None, 0)),
    ):
        stream.run(stop_event=stop_event)

    assert stop_event.waits == [2]


def test_scoreboard_stops_cooperatively_while_unconfigured():
    stop_event = StopAfterFirstWait()
    config = mock.Mock(public_scoreboard_url=None, hooks=[])

    with (
        mock.patch("rcon.api_commands.get_rcon_api", return_value=mock.Mock()),
        mock.patch.object(
            scoreboard.ScoreboardUserConfig,
            "load_from_db",
            return_value=config,
        ),
    ):
        scoreboard.run(stop_event=stop_event)

    assert stop_event.waits == [scoreboard.SCOREBOARD_CONFIG_RETRY_SECONDS]


def test_automod_stops_cooperatively():
    stop_event = StopAfterFirstWait()

    with (
        mock.patch.object(automod, "get_rcon", return_value=mock.Mock()),
        mock.patch.object(automod, "get_redis_client", return_value=mock.Mock()),
        mock.patch.object(automod, "punish_squads") as punish,
    ):
        automod.run(stop_event=stop_event)

    assert stop_event.waits == [5]
    punish.assert_called_once()


def test_watch_killrate_stays_available_and_stops_when_disabled():
    stop_event = StopAfterFirstWait()
    config = mock.Mock(enabled=False)

    with (
        mock.patch.object(watch_killrate, "get_rcon_api", return_value=mock.Mock()),
        mock.patch.object(
            watch_killrate.RconServerSettingsUserConfig,
            "load_from_db",
            return_value=mock.Mock(),
        ),
        mock.patch.object(
            watch_killrate.WatchKillRateUserConfig,
            "load_from_db",
            return_value=config,
        ),
    ):
        watch_killrate.run(stop_event=stop_event)

    assert stop_event.waits == [5]


def test_seed_vip_stays_available_and_stops_when_disabled():
    stop_event = StopAfterFirstWait()
    config = seed_vip.SeedVIPUserConfig(enabled=False, language=None)
    outbox = mock.Mock()

    with (
        mock.patch.object(seed_vip, "get_rcon_api", return_value=mock.Mock()),
        mock.patch.object(seed_vip, "NotificationOutbox", return_value=outbox),
        mock.patch.object(
            seed_vip.SeedVIPUserConfig,
            "load_from_db",
            return_value=config,
        ),
    ):
        seed_vip.run(stop_event=stop_event)

    assert stop_event.waits == [5]
    outbox.clear.assert_called_once()


def test_vip_rewards_stops_cooperatively():
    stop_event = StopAfterFirstWait()
    session = mock.Mock()
    session.query.return_value.filter_by.return_value = []

    with (
        mock.patch("rcon.api_commands.get_rcon_api", return_value=mock.Mock()),
        mock.patch.object(vip_rewards, "lock", return_value=nullcontext()),
        mock.patch.object(
            vip_rewards,
            "enter_session",
            return_value=nullcontext(session),
        ),
        mock.patch.object(vip_rewards, "tick") as tick,
        mock.patch.object(vip_rewards.time, "monotonic", side_effect=[0, 0]),
    ):
        vip_rewards.run(stop_event=stop_event)

    assert stop_event.waits == [30]
    tick.assert_called_once()
