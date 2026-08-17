from unittest import mock

from rcon import auto_settings, broadcast


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
