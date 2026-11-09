import os
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")

from rcon import workers


def log(timestamp, message="same kill"):
    return {
        "event_time": datetime.fromtimestamp(timestamp, UTC),
        "message": message,
        "raw": f"[{timestamp}] {message}",
    }


@pytest.mark.parametrize("server_retained", [True, False])
def test_backfill_saves_missing_structured_events_not_database_rows(
    monkeypatch, server_retained
):
    session = Mock()
    recorder = Mock()
    rcon = Mock()
    present, missing, cached_only = log(1_100), log(1_101), log(1_102, "cache only")
    rcon.get_structured_logs.return_value = {
        "logs": [present, missing] if server_retained else []
    }
    monkeypatch.setattr(workers, "get_rcon", lambda: rcon)
    monkeypatch.setattr(workers, "enter_session", lambda: nullcontext(session))
    monkeypatch.setattr(workers, "_are_match_logs_available", lambda *args: True)
    monkeypatch.setattr(
        workers,
        "LogsHistory",
        lambda: [present, missing, cached_only, log(999), log(2_001)],
    )
    monkeypatch.setattr(workers, "LogRecorder", lambda: recorder)
    monkeypatch.setattr(
        workers,
        "get_historical_logs_records",
        lambda *args, **kwargs: [
            SimpleNamespace(
                event_time=present["event_time"].replace(tzinfo=None),
                content=present["message"],
            ),
            SimpleNamespace(
                event_time=datetime.fromtimestamp(1_099, UTC), content="DB only"
            ),
        ],
    )

    workers.save_missing_match_logs({"start": 1_000, "end": 2_000})

    recorder._save_logs.assert_called_once_with(session, [missing, cached_only])


def test_backfill_does_not_collapse_repeated_messages(monkeypatch):
    session, recorder, rcon = Mock(), Mock(), Mock()
    rcon.get_structured_logs.return_value = {
        "logs": [log(1_001), log(1_002), log(1_002)]
    }
    monkeypatch.setattr(workers, "get_rcon", lambda: rcon)
    monkeypatch.setattr(workers, "enter_session", lambda: nullcontext(session))
    monkeypatch.setattr(workers, "_are_match_logs_available", lambda *args: True)
    monkeypatch.setattr(workers, "LogsHistory", lambda: [])
    monkeypatch.setattr(workers, "LogRecorder", lambda: recorder)
    monkeypatch.setattr(
        workers, "get_historical_logs_records", lambda *args, **kwargs: []
    )

    workers.save_missing_match_logs({"start": 1_000, "end": 2_000})

    recorder._save_logs.assert_called_once_with(session, [log(1_001), log(1_002)])


def test_backfill_older_than_one_day_does_not_wrap_time_window(monkeypatch):
    now = datetime.now(UTC)
    start = int((now - timedelta(days=2, minutes=5)).timestamp())
    rcon = Mock()
    rcon.get_structured_logs.return_value = {"logs": []}
    monkeypatch.setattr(workers, "get_rcon", lambda: rcon)
    monkeypatch.setattr(workers, "enter_session", lambda: nullcontext(Mock()))
    monkeypatch.setattr(workers, "_are_match_logs_available", lambda *args: True)
    monkeypatch.setattr(workers, "LogsHistory", lambda: [])
    monkeypatch.setattr(
        workers, "get_historical_logs_records", lambda *args, **kwargs: []
    )

    workers.save_missing_match_logs({"start": start, "end": start + 5_400})

    assert rcon.get_structured_logs.call_args.kwargs["since_min_ago"] >= 2 * 24 * 60 + 5
