"""Exercise the real command send/receive path with synthetic transport errors."""

import threading
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon.commands import HLLServerCtl
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
def test_kick_is_not_retransmitted_on_uncertain_transport(controller, failure_at):
    api, connection = controller
    handle = Mock()
    handle.request = SimpleNamespace(name="KickPlayer", version=2, content="")
    connection.send.return_value = handle
    if failure_at == "send":
        connection.send.side_effect = OSError("socket lost after write")
    else:
        handle.receive.side_effect = OSError("acknowledgement lost")
    with api.without_retries(), pytest.raises(OSError):
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
