from collections import defaultdict
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

from rcon.seed_vip.utils import calc_vip_expiration_timestamp, has_indefinite_vip, reward_players
from rcon.user_config.seed_vip import SeedVIPUserConfig


def test_cumulative_reward_starts_no_earlier_than_award_time():
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    config = SeedVIPUserConfig(reward={"cumulative": True, "timeframe": {"days": 1}})
    assert calc_vip_expiration_timestamp(config, now-timedelta(days=7), now) == now+timedelta(days=1)


def test_existing_vip_without_expiration_is_indefinite():
    assert has_indefinite_vip(SimpleNamespace(expiration_date=None)) is True
    assert has_indefinite_vip(None) is False


def test_rejected_or_uncertain_rewards_do_not_stop_others_or_report_success(monkeypatch):
    from rcon.vip_rewards import locking, service
    now = datetime(2026, 1, 10, tzinfo=timezone.utc)
    config = SeedVIPUserConfig(dry_run=False)
    api = Mock()
    def award(**kwargs):
        if kwargs["player_id"] == "rejected": return False
        if kwargs["player_id"] == "uncertain": raise TimeoutError("lost response")
        return True
    api.add_vip.side_effect = award
    monkeypatch.setattr(locking, "vip_lock", lambda _: nullcontext())
    monkeypatch.setattr(service, "current_vip", lambda *_: None)
    ids = {"accepted", "rejected", "uncertain"}
    result = reward_players(api, config, ids, {}, {p: p for p in ids}, defaultdict(lambda: now), reward_time=now)
    assert result == {"accepted"}
    assert {call.kwargs["player_id"] for call in api.add_vip.call_args_list} == ids
