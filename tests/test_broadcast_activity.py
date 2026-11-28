import os
os.environ.setdefault('SERVER_NUMBER','1')
os.environ.setdefault('DEBUG','1')
from unittest.mock import Mock, MagicMock
from rcon import broadcast as b
from rcon import broadcast_activity as a
from rcon.user_config.auto_broadcast import AutoBroadcastUserConfig

class SimulatedClock:
    def __init__(self, until=500):
        self.now = 0
        self.until = until

    def is_set(self):
        return self.now >= self.until

    def wait(self, seconds):
        self.now += seconds
        return self.is_set()


def test_interval_change_shortens_existing_slot(monkeypatch):
    cfg = AutoBroadcastUserConfig(enabled=True, messages=[{'time_sec': 900, 'message': 'one'}])
    new = AutoBroadcastUserConfig(enabled=True, messages=[{'time_sec': 30, 'message': 'one'}])
    clock = SimulatedClock()
    monkeypatch.setattr(b.time, 'monotonic', lambda: clock.now)
    monkeypatch.setattr(b.AutoBroadcastUserConfig, 'load_from_db', lambda: new)
    monkeypatch.setattr(b, 'update_state', Mock())
    b.wait_for_campaign(clock, 'legacy:0', cfg.messages[0])
    assert clock.now == 30


def test_disabled_settings_interrupt_wait(monkeypatch):
    cfg = AutoBroadcastUserConfig(enabled=True, messages=[{'time_sec': 900, 'message': 'one'}])
    clock = SimulatedClock()
    monkeypatch.setattr(b.time, 'monotonic', lambda: clock.now)
    monkeypatch.setattr(b.AutoBroadcastUserConfig, 'load_from_db', lambda: AutoBroadcastUserConfig(enabled=False))
    monkeypatch.setattr(b, 'update_state', Mock())
    b.wait_for_campaign(clock, 'legacy:0', cfg.messages[0])
    assert clock.now == b.CHECK_INTERVAL

def test_cache_failure_never_causes_delivery_retry(monkeypatch):
    monkeypatch.setattr(a,'get_redis_client',Mock(side_effect=RuntimeError('unavailable')))
    campaign=Mock(id='x',title='test')
    a.record_attempt(campaign,'hello',True)
    a.update_state('waiting',123)
    assert a.get_status()['available'] is False

def test_history_is_bounded_and_expires(monkeypatch):
    red=MagicMock();pipe=red.pipeline.return_value.__enter__.return_value
    monkeypatch.setattr(a,'get_redis_client',lambda:red)
    a.record_attempt(Mock(id='x',title='test'),'hello',False,'TimeoutError')
    pipe.ltrim.assert_called_once_with(a.HISTORY,0,199)
    pipe.expire.assert_called_once_with(a.HISTORY,86400)
    assert 'unconfirmed' in pipe.lpush.call_args.args[1]

def test_manual_text_does_not_block_campaign(monkeypatch):
    monkeypatch.setattr(b,'load_rotation',lambda:[])
    monkeypatch.setattr(b,'save_rotation',Mock())
    cfg=AutoBroadcastUserConfig(enabled=True,messages=[{'time_sec':1,'message':'hello'}])
    monkeypatch.setattr(b.AutoBroadcastUserConfig,'load_from_db',lambda:cfg)
    monkeypatch.setattr(b,'update_state',Mock());record=Mock();monkeypatch.setattr(b,'record_attempt',record)
    monkeypatch.setattr(b,'manual_broadcast_is_active',Mock(side_effect=AssertionError('must not block')))
    ctl=Mock();ctl.get_slots.return_value={'current_players':10}
    monkeypatch.setattr('rcon.rcon.get_rcon',lambda:ctl)
    monkeypatch.setattr(b,'format_message',lambda ctl,msg:msg)
    import threading
    stop=threading.Event()
    def wait(*args):stop.set();return True
    monkeypatch.setattr(b,'wait_for_campaign',wait)
    b.run(stop)
    ctl._send_rendered_broadcast.assert_called_once_with('hello', cached_text='hello')
    assert record.call_args.args[2] is True

import pytest
@pytest.mark.parametrize("previous", [b"old", "old", None])
def test_broadcast_accepts_both_redis_response_types(monkeypatch, previous):
    from rcon.rcon import Rcon, ServerCtl
    ctl=object.__new__(Rcon)
    red=Mock();red.set.return_value=previous
    monkeypatch.setattr('rcon.rcon.get_redis_client',lambda:red)
    monkeypatch.setattr(b,'format_message',lambda ctl,msg:msg)
    send=Mock();monkeypatch.setattr(ServerCtl,'set_broadcast',send)
    assert ctl.set_broadcast('hello') == ('old' if previous else '')
    send.assert_called_once_with('hello')

def _campaigns(*entries):
    return AutoBroadcastUserConfig(
        enabled=True, messages=[
            {"id": name, "message": name, "time_sec": seconds} for name, seconds in entries
        ],
    )


def _run_rotation(monkeypatch, config, clock, *, restored=(), slots=None, send=None):
    monkeypatch.setattr(b.time, "monotonic", lambda: clock.now)
    monkeypatch.setattr(b.AutoBroadcastUserConfig, "load_from_db", staticmethod(config))
    monkeypatch.setattr(b, "load_rotation", lambda: list(restored))
    checkpoints = []
    monkeypatch.setattr(b, "save_rotation", lambda keys: checkpoints.append(tuple(keys)))
    monkeypatch.setattr(b, "update_state", Mock())
    audit = Mock()
    monkeypatch.setattr(b, "record_attempt", audit)
    monkeypatch.setattr(b, "format_message", lambda ctl, message: message)
    ctl = Mock()
    ctl.get_slots.side_effect = slots or (lambda: {"current_players": 15})
    attempts = []

    def publish(message, *, cached_text):
        assert cached_text == message
        attempts.append((message, clock.now))
        if send:
            send(message)

    ctl._send_rendered_broadcast.side_effect = publish
    monkeypatch.setattr("rcon.rcon.get_rcon", lambda: ctl)
    b.run(clock)
    return attempts, checkpoints, audit


def test_changing_private_settings_does_not_restart_or_truncate_rotation(monkeypatch):
    clock = SimulatedClock(until=128)

    def config():
        cfg = _campaigns(("VIP", 45), ("Language", 32), ("Stats", 51))
        cfg.player_message_interval_sec = 10 + int(clock.now) % 40
        return cfg

    attempts, _, _ = _run_rotation(monkeypatch, config, clock)
    assert attempts == [("VIP", 0), ("Language", 45), ("Stats", 77)]


def test_active_interval_edit_uses_original_start_and_then_reaches_next_slot(monkeypatch):
    clock = SimulatedClock(until=45)

    def config():
        return _campaigns(("VIP", 1800 if clock.now == 0 else 30), ("Language", 15))

    attempts, _, _ = _run_rotation(monkeypatch, config, clock)
    assert attempts == [("VIP", 0), ("Language", 30)]


def test_resume_unattempted_slots_skips_removed_campaigns_and_loads_new_text(monkeypatch):
    clock = SimulatedClock(until=60)

    def config():
        cfg = _campaigns(("VIP", 60), ("Language", 30), ("Stats", 30))
        cfg.messages[1].message = "Updated language prompt"
        return cfg

    attempts, checkpoints, _ = _run_rotation(
        monkeypatch, config, clock, restored=["id:removed", "id:Language", "id:Stats"],
    )
    assert attempts == [("Updated language prompt", 0), ("Stats", 30)]
    assert checkpoints == [("id:Stats",), ()]


def test_rejected_slow_slot_advances_promptly_then_is_retried_next_round(monkeypatch):
    clock = SimulatedClock(until=52)
    cfg = _campaigns(("VIP", 1800), ("Language", 30))
    def reject_bad_slot(message):
        if message == "VIP":
            raise TimeoutError("no acknowledgement")

    attempts, _, audit = _run_rotation(monkeypatch, lambda: cfg, clock, send=reject_bad_slot)
    assert attempts == [("VIP", 0), ("Language", 20), ("VIP", 50)]
    assert [call.args[2] for call in audit.call_args_list] == [False, True, False]


def test_server_disconnect_keeps_next_slot_until_connection_recovers(monkeypatch):
    clock = SimulatedClock(until=80)
    cfg = _campaigns(("VIP", 60), ("Language", 60))
    attempts, _, audit = _run_rotation(
        monkeypatch, lambda: cfg, clock, restored=["id:Language"],
        slots=[ConnectionResetError(), {"current_players": 99}],
    )
    assert attempts == [("Language", 20)]
    assert audit.call_count == 1


def test_rejected_native_response_never_replaces_last_acknowledged_text(monkeypatch):
    from rcon.rcon import Rcon
    from rcon.connection import Response, ResponseStatus, HLLCommandError

    ctl = object.__new__(Rcon)
    ctl.auto_retry = False
    ctl.perf_stats = Mock()
    ctl.send = Mock()
    ctl.send.return_value.receive.return_value = Response(
        1, "ServerBroadcast", 2, ResponseStatus.BAD_REQUEST, "Rejected", ""
    )
    redis = Mock()
    monkeypatch.setattr("rcon.rcon.get_redis_client", lambda: redis)
    monkeypatch.setattr(b, "format_message", lambda ctl, msg: msg)
    with pytest.raises(HLLCommandError) as exc:
        ctl.set_broadcast("rejected text")
    assert exc.value.status_code == 400
    redis.set.assert_not_called()


def test_redis_failure_after_native_ack_does_not_turn_success_into_failure(monkeypatch):
    from rcon.rcon import Rcon, ServerCtl
    from rcon.connection import Response, ResponseStatus

    ctl = object.__new__(Rcon)
    send = Mock(return_value=Response(1, "ServerBroadcast", 2, ResponseStatus.OK, "OK", ""))
    monkeypatch.setattr(ServerCtl, "exchange", send)
    monkeypatch.setattr("rcon.rcon.get_redis_client", Mock(side_effect=OSError("Redis offline")))
    monkeypatch.setattr(b, "format_message", lambda ctl, msg: msg)
    assert ctl.set_broadcast("Hello") == ""
    send.assert_called_once_with("ServerBroadcast", 2, {"Message": "Hello"})


@pytest.mark.parametrize("cached,expected", [
    (b'["id:two"]', ["id:two"]), (None, []), (b'{"bad":true}', []), (b'corrupt', []),
])
def test_restore_rotation_handles_absent_or_stale_checkpoint(monkeypatch, cached, expected):
    redis = Mock()
    redis.get.return_value = cached
    monkeypatch.setattr(a, "get_redis_client", lambda: redis)
    assert a.load_rotation() == expected


def test_configuration_outage_during_slot_recovers_in_same_worker(monkeypatch):
    cfg = _campaigns(("VIP", 65), ("Language", 10))
    clock = SimulatedClock(until=75)

    def config():
        if clock.now == 20:
            raise OSError("settings temporarily unavailable")
        return cfg

    attempts, _, _ = _run_rotation(monkeypatch, config, clock)
    assert attempts == [("VIP", 0), ("Language", 65)]


def test_removed_and_new_campaigns_are_reconciled_without_starving_last_slot(monkeypatch):
    clock = SimulatedClock(until=70)
    old = _campaigns(("VIP", 20), ("Old", 20), ("Language", 10))
    new = _campaigns(("VIP", 20), ("New", 10), ("Language", 10))
    attempts, _, _ = _run_rotation(monkeypatch, lambda: old if clock.now == 0 else new, clock)
    assert attempts == [("VIP", 0), ("Language", 20), ("VIP", 30), ("New", 50), ("Language", 60)]


def test_permanent_protocol_rejection_backs_off_even_on_one_second_campaign(monkeypatch):
    from rcon.connection import HLLCommandError
    cfg = _campaigns(("Broken", 1))
    clock = SimulatedClock(until=45)

    def reject(message):
        raise HLLCommandError(400, "invalid message")

    attempts, _, audit = _run_rotation(monkeypatch, lambda: cfg, clock, send=reject)
    assert attempts == [("Broken", 0), ("Broken", 20), ("Broken", 40)]
    assert all(call.args[2:] == (False, "RCON 400") for call in audit.call_args_list)


def test_redis_checkpoint_failure_is_advisory(monkeypatch):
    monkeypatch.setattr(a, "get_redis_client", Mock(side_effect=TimeoutError("redis unreachable")))
    assert a.load_rotation() == []
    a.save_rotation(["id:Language"])
