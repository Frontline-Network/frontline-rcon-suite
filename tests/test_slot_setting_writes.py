from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon.rcon import HLLCommandFailedError, HLLRcon, HLLVRcon
from rcon import rcon as module


@pytest.mark.parametrize("controller", [HLLRcon, HLLVRcon])
@pytest.mark.parametrize(
    "method,key,command,parameter,value",
    [
        (
            "set_queue_length",
            "maxQueueCount",
            "SetMaxQueuedPlayers",
            "MaxQueuedPlayers",
            6,
        ),
        ("set_vip_slots_num", "maxVipQueueCount", "SetVipSlotCount", "VipSlotCount", 2),
    ],
)
def test_slot_writes_require_a_fresh_difference(
    monkeypatch, controller, method, key, command, parameter, value
):
    api = object.__new__(controller)
    api.exchange = Mock(return_value=SimpleNamespace(content_dict={key: value}))
    # A stale UI cache must never decide whether to write.
    setattr(
        api,
        method.replace("set_", "get_"),
        Mock(side_effect=AssertionError("cached getter used")),
    )
    invalidation = Mock(side_effect=lambda *_: nullcontext())
    monkeypatch.setattr(module, "invalidates_for", invalidation)
    assert getattr(api, method)(value) is True
    api.exchange.assert_called_once_with(
        "GetServerInformation", 2, {"Name": "session", "Value": ""}
    )
    invalidation.assert_called_once()

    api.exchange.reset_mock()
    api.exchange.return_value = SimpleNamespace(content_dict={key: value + 1})
    assert getattr(api, method)(value) is True
    assert api.exchange.call_count == 2
    api.exchange.assert_called_with(command, 2, {parameter: value})


@pytest.mark.parametrize("controller", [HLLRcon, HLLVRcon])
@pytest.mark.parametrize("method", ["set_queue_length", "set_vip_slots_num"])
def test_failed_read_never_triggers_a_slot_write(monkeypatch, controller, method):
    api = object.__new__(controller)
    api.exchange = Mock(side_effect=TimeoutError("read failed"))
    monkeypatch.setattr(module, "invalidates_for", lambda *_: nullcontext())
    with pytest.raises(TimeoutError):
        getattr(api, method)(2)
    assert api.exchange.call_count == 1
    assert api.exchange.call_args.args[0] == "GetServerInformation"


@pytest.mark.parametrize("controller", [HLLRcon, HLLVRcon])
def test_drift_is_rechecked_on_every_call(monkeypatch, controller):
    api = object.__new__(controller)
    monkeypatch.setattr(module, "invalidates_for", lambda *_: nullcontext())
    actual = 2
    writes = []

    def exchange(command, version, body):
        if command == "SetVipSlotCount":
            writes.append(body["VipSlotCount"])
        return SimpleNamespace(content_dict={"maxVipQueueCount": actual})

    api.exchange = exchange
    api.set_vip_slots_num(2)
    actual = 5
    api.set_vip_slots_num(2)
    actual = 2
    api.set_vip_slots_num(2)
    assert writes == [2]


@pytest.mark.parametrize("value", [None, "2", True, -1])
@pytest.mark.parametrize(
    "method,key",
    [("set_vip_slots_num", "maxVipQueueCount"), ("set_queue_length", "maxQueueCount")],
)
def test_invalid_live_value_never_triggers_a_write(monkeypatch, method, key, value):
    api = object.__new__(HLLVRcon)
    api.exchange = Mock(return_value=SimpleNamespace(content_dict={key: value}))
    monkeypatch.setattr(module, "invalidates_for", lambda *_: nullcontext())
    with pytest.raises(HLLCommandFailedError):
        getattr(api, method)(2)
    assert api.exchange.call_count == 1
