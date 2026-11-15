"""Exercise the real command send/receive path with synthetic transport errors."""

import threading
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon.commands import HLLServerCtl
from rcon.connection import HLLBrokenConnectionError
from rcon.types import ServerInfo


@pytest.fixture
def controller(monkeypatch):
    api = HLLServerCtl(
        ServerInfo(host="127.0.0.1", port=12345, password="test"), Mock()
    )
    connection = Mock()
    monkeypatch.setattr(api, "with_connection", lambda: nullcontext(connection))
    monkeypatch.setattr(api, "_retry_delay", Mock(return_value=0))
    return api, connection


@pytest.mark.parametrize("failure_at", ["send", "receive"])
@pytest.mark.parametrize("error_type", [OSError, HLLBrokenConnectionError])
def test_kick_is_not_retransmitted_on_uncertain_transport(
    controller, failure_at, error_type
):
    api, connection = controller
    handle = Mock()
    handle.request = SimpleNamespace(name="KickPlayer", version=2, content="")
    connection.send.return_value = handle
    if failure_at == "send":
        connection.send.side_effect = error_type("socket lost after write")
    else:
        handle.receive.side_effect = error_type("acknowledgement lost")
    with api.without_retries(), pytest.raises(error_type):
        api.kick("synthetic-player", "Test only")
    assert connection.send.call_count == 1
    connection.exchange.assert_not_called()
    api._retry_delay.assert_not_called()


@pytest.mark.parametrize("method", ["receive", "receive_optional"])
def test_both_receive_paths_honor_scope(controller, method):
    api, connection = controller
    handle = Mock()
    handle.request = SimpleNamespace(name="test", version=2, content="")
    handle.receive.side_effect = OSError("lost")
    with api.without_retries():
        with api.without_retries(), pytest.raises(OSError):
            getattr(api, method)(handle)
        with pytest.raises(OSError):
            getattr(api, method)(handle)
    connection.exchange.assert_not_called()
    # Exiting the scope restores existing retry behavior, even after errors.
    getattr(api, method)(handle)
    connection.exchange.assert_called_once()


def test_disabling_retries_does_not_change_other_supervisor_threads(controller):
    api, connection = controller
    handle = Mock()
    handle.request = SimpleNamespace(name="test", version=2, content="")
    handle.receive.side_effect = OSError("lost")
    errors = []

    def other_worker():
        try:
            api.receive(handle)
        except Exception as error:
            errors.append(error)

    with api.without_retries():
        worker = threading.Thread(target=other_worker)
        worker.start()
        worker.join(timeout=2)
        assert not worker.is_alive()
    assert errors == []
    connection.exchange.assert_called_once()


@pytest.mark.parametrize("command", ["MessagePlayer", "PunishPlayer", "ForceTeamSwitch", "KickPlayer", "AddMapToRotation", "RemoveMapFromRotation", "AddMapToSequence", "RemoveMapFromSequence", "MoveMapInSequence"])
@pytest.mark.parametrize("method", ["receive", "receive_optional"])
def test_side_effect_command_is_not_retried_after_lost_response(command, method):
    api = HLLServerCtl(ServerInfo(host="127.0.0.1", port=12345, password="test"), Mock())
    connection = Mock()
    api.with_connection = Mock(return_value=nullcontext(connection))
    handle = Mock()
    handle.request = SimpleNamespace(name=command, version=2, content={})
    handle.receive.side_effect = OSError("response lost")
    with pytest.raises(OSError, match="response lost"):
        getattr(api, method)(handle)
    connection.exchange.assert_not_called()


@pytest.mark.parametrize("command", ["MessagePlayer", "PunishPlayer", "ForceTeamSwitch"])
def test_side_effect_command_is_not_retried_after_send_error(command):
    api = HLLServerCtl(ServerInfo(host="127.0.0.1", port=12345, password="test"), Mock())
    connection = Mock()
    connection.send.side_effect = OSError("uncertain send")
    api.with_connection = Mock(return_value=nullcontext(connection))
    with pytest.raises(OSError, match="uncertain send"):
        api.send(command, 2, {})
    connection.send.assert_called_once()
