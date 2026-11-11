import os
os.environ.setdefault('SERVER_NUMBER','1')
os.environ.setdefault('DEBUG','1')
from unittest.mock import Mock, MagicMock
from rcon import broadcast as b
from rcon import broadcast_activity as a
from rcon.user_config.auto_broadcast import AutoBroadcastUserConfig

def test_interval_change_interrupts_old_wait(monkeypatch):
    old=AutoBroadcastUserConfig(enabled=True,messages=[{'time_sec':900,'message':'one'}])
    new=AutoBroadcastUserConfig(enabled=True,messages=[{'time_sec':30,'message':'one'}])
    monkeypatch.setattr(b.AutoBroadcastUserConfig,'load_from_db',lambda:new)
    monkeypatch.setattr(b,'update_state',Mock())
    stop=Mock();stop.is_set.return_value=False;stop.wait.return_value=False
    assert b.wait_for_campaign(stop,old,900)
    assert stop.wait.call_args.args[0] <= 20

def test_disabled_settings_interrupt_wait(monkeypatch):
    old=AutoBroadcastUserConfig(enabled=True,messages=[])
    monkeypatch.setattr(b.AutoBroadcastUserConfig,'load_from_db',lambda:AutoBroadcastUserConfig(enabled=False,messages=[]))
    monkeypatch.setattr(b,'update_state',Mock())
    stop=Mock();stop.is_set.return_value=False;stop.wait.return_value=False
    assert b.wait_for_campaign(stop,old,900)

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
    ctl.set_broadcast.assert_called_once_with('hello')
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
