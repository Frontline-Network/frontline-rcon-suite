"""Real PostgreSQL races, isolated schema; explicit test DB opt-in required."""

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from rcon import admin_incidents as incidents
from rcon.leadership_vote import storage, service
from rcon.models import (
    AdminIncident,
    AdminIncidentSubject,
    AdminIncidentEvent,
    LeadershipVote,
    LeadershipMessage,
    UserConfig,
)
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig as Config
from tests.test_leadership_vote import (
    NOW,
    TABLES,
    roster,
    report,
    activate,
    observe_for,
    context,
    elapse,
    vote,
)


@pytest.fixture
def postgres(monkeypatch):
    url = os.getenv("LEADERSHIP_VOTE_TEST_DB_URL")
    if not url:
        pytest.skip(
            "Set LEADERSHIP_VOTE_TEST_DB_URL to a disposable PostgreSQL test database"
        )
    engine = create_engine(url)
    if engine.dialect.name != "postgresql":
        pytest.fail("Concurrency tests require real PostgreSQL")
    schema = "leadership_test_" + uuid.uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped = engine.execution_options(schema_translate_map={None: schema})
    for model in TABLES:
        model.__table__.create(scoped)
    sessions = sessionmaker(scoped, expire_on_commit=False)

    @contextmanager
    def session():
        with sessions.begin() as sess:
            yield sess

    session.clock = SimpleNamespace(now=NOW)
    monkeypatch.setattr(storage, "discord_ready", lambda sess: True)
    monkeypatch.setattr(storage, "report_delivered", lambda sess, vote: True)
    for module in (storage, service, incidents):
        monkeypatch.setattr(module, "enter_session", session)
    from datetime import datetime, timezone

    monkeypatch.setattr(
        incidents,
        "_utcnow",
        lambda: datetime.fromtimestamp(session.clock.now, timezone.utc),
    )
    monkeypatch.setattr(storage.time, "time", lambda: session.clock.now)
    storage.configure(1, Config(enabled=True), "test")
    try:
        yield session
    finally:
        # Generated identifier is fixed-prefix hex, never a user/database path.
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def test_parallel_reports_ballots_and_deadlines_are_serialized(postgres):
    players = roster()
    observe_for(postgres, players)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(
                lambda i: report(players, text=f"!admin Able redet nicht ({i})"),
                range(8),
            )
        )
    linked = [r for r in results if r["leadership_vote"]]
    assert len(linked) == 1
    storage.recover(1)
    # No warning had started, so the next independent test vote has no cooldown.
    vid, players = activate(postgres, 6, mode="active")
    postgres.clock.now += 1
    with ThreadPoolExecutor(max_workers=6) as pool:
        assert all(
            pool.map(
                lambda i: storage.ballot(
                    1, f"v{i}", True, postgres.clock.now, players, "round-1"
                ),
                range(6),
            )
        )
    assert vote(postgres, vid)["yes"] == 6
    elapse(postgres, players, 120)
    with ThreadPoolExecutor(max_workers=8) as pool:
        jobs = list(pool.map(lambda _: storage.advance(1, context(players)), range(8)))
    assert sum(len(job) for job in jobs) == 1
    with ThreadPoolExecutor(max_workers=8) as pool:
        sent = list(
            pool.map(lambda _: storage.begin_send(1, vid, context(players)), range(8))
        )
    assert sum(sent) == 1


def test_takeover_and_committed_send_marker_cannot_both_win(postgres):
    vid, players = activate(postgres, 3, mode="active")
    postgres.clock.now += 1
    for i in range(2):
        assert storage.ballot(1, f"v{i}", True, postgres.clock.now, players, "round-1")
    elapse(postgres, players, 120)
    assert storage.advance(1, context(players))

    def takeover():
        try:
            storage.cancel(1, vid, "moderator")
            return True
        except incidents.IncidentConflict:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        manual = pool.submit(takeover)
        automatic = pool.submit(storage.begin_send, 1, vid, context(players))
        assert manual.result() != automatic.result()
