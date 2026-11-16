import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DEBUG", "1")

from rcon import campaign_delivery, vip_lifecycle
from rcon.user_config.auto_broadcast import AutoBroadcastMessage, VipLifecycleCampaign


@pytest.mark.parametrize("module", [campaign_delivery, vip_lifecycle])
@pytest.mark.parametrize("start_seconds", [1711846200, 1729990200])
def test_active_session_uses_absolute_start_across_dst(monkeypatch, module, start_seconds):
    # These instants are shortly before Berlin's spring and autumn DST changes.
    start = datetime.fromtimestamp(start_seconds, timezone.utc)
    player = SimpleNamespace(id=7, player_id="player-1")
    session = SimpleNamespace(
        id=11,
        start=datetime(2024, 3, 31, 1, 30),  # legacy wall time is not UTC
        start_event_us=start_seconds * 1_000_000,
        created=datetime(2024, 3, 31),
    )

    class Query:
        def join(self, *args): return self
        def filter(self, *args): return self
        def order_by(self, *args): return self
        def all(self): return [(player, session)]

    @contextmanager
    def fake_session():
        yield SimpleNamespace(query=lambda *args: Query())

    monkeypatch.setattr(module, "enter_session", fake_session)
    result = module._active_sessions({"player-1"}, 1)["player-1"]
    if module is campaign_delivery:
        item = AutoBroadcastMessage(id="dst", message="hello", time_sec=60, min_session_minutes=30)
        eligible = module.session_is_eligible
        utc_start = start.replace(tzinfo=None)
    else:
        item = VipLifecycleCampaign(message="hello", min_session_minutes=30)
        eligible = module._session_is_eligible
        utc_start = start
    assert result["start"] == utc_start
    assert not eligible(item, result["start"], utc_start + timedelta(minutes=29, seconds=59))
    assert eligible(item, result["start"], utc_start + timedelta(minutes=30))


@pytest.mark.parametrize("module", [campaign_delivery, vip_lifecycle])
def test_legacy_session_uses_utc_creation_as_conservative_start(monkeypatch, module):
    player = SimpleNamespace(id=7, player_id="player-1")
    legacy_start = datetime(2024, 10, 27, 2, 30)
    created_utc = datetime(2024, 10, 27, 1, 31)
    session = SimpleNamespace(id=11, start=legacy_start, start_event_us=None, created=created_utc)

    class Query:
        def join(self, *args): return self
        def filter(self, *args): return self
        def order_by(self, *args): return self
        def all(self): return [(player, session)]

    @contextmanager
    def fake_session():
        yield SimpleNamespace(query=lambda *args: Query())

    monkeypatch.setattr(module, "enter_session", fake_session)
    start = module._active_sessions({"player-1"}, 1)["player-1"]["start"]
    assert start == created_utc
    if module is campaign_delivery:
        item = AutoBroadcastMessage(id="legacy", message="hello", time_sec=60, min_session_minutes=5)
        eligible = module.session_is_eligible
    else:
        item = VipLifecycleCampaign(message="hello", min_session_minutes=5)
        eligible = module._session_is_eligible
    assert not eligible(item, start, created_utc + timedelta(minutes=4, seconds=59))
    assert eligible(item, start, created_utc + timedelta(minutes=5))
    assert not eligible(item, None, created_utc + timedelta(days=1))
