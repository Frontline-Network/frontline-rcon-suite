"""Opt-in concurrent reminder integration with synthetic players and PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
import os
from threading import Lock
import time
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from rcon.vote_map import reminder_delivery as journal
from rcon.vote_map import service


@pytest.mark.skipif(not os.environ.get("RCON_VOTEMAP_TEST_DATABASE"), reason="requires isolated PostgreSQL")
def test_concurrent_workers_send_each_recipient_once(monkeypatch):
    base = create_engine(os.environ["RCON_VOTEMAP_TEST_DATABASE"])
    schema = "votemap_integration_" + uuid.uuid4().hex
    with base.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = base.execution_options(schema_translate_map={None: schema})
    try:
        journal.metadata.create_all(engine)
        sessions = sessionmaker(engine)
        monkeypatch.setattr(journal, "get_session_maker", lambda: sessions)
        monkeypatch.setattr(service, "get_server_number", lambda: 3)
        calls, call_lock = [], Lock()

        class SyntheticServer:
            def without_retries(self):
                return nullcontext()

            def message_player(self, *, player_id, message):
                with call_lock:
                    calls.append((player_id, message))
                time.sleep(0.05)
                return True

        vote = SimpleNamespace(
            config=SimpleNamespace(instruction_text="Vote: {map_selection}", reminder_frequency_minutes=20),
            _maps_history=[{"name": "synthetic", "start": 123}], paused=False,
            _rcon=SyntheticServer(),
            _get_optin_players=lambda: [("Alice", "fake-a"), ("Bob", "fake-b")],
            has_player_voted=lambda _pid: False,
            format_map_vote=lambda **_kw: "maps",
            get_selection=lambda: [], get_votes=lambda: [], get_player_choice=lambda: None,
            set_last_reminder_time=lambda: None,
            is_time_for_reminder=lambda: True,
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: service.VoteMap.send_reminder.__wrapped__(
                vote, force=True, scope="event:start:123"), range(2)))
        assert sorted(calls) == [("fake-a", "Vote: maps"), ("fake-b", "Vote: maps")]
        assert any(result.ok for result in results)
        assert all(result.ok or result.outcome in {service.ActionOutcome.ON_COOLDOWN, service.ActionOutcome.PARTIAL}
                   for result in results)
    finally:
        with base.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        base.dispose()
