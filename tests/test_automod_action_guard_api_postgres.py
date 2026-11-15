"""Guard review is restricted to authorized operators and the active server."""
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from tests.test_session_event_api_postgres import invoke
from rcon.automods import action_guard


@pytest.fixture
def guard_api(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "automod_api_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    action_guard.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(action_guard, "get_session_maker", lambda: maker)
    monkeypatch.setattr("rcon.api_commands.get_server_number", lambda: "3")
    try:
        yield maker
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def test_guard_review_requires_permissions_and_audits_actor(guard_api):
    token = action_guard.reserve(3, "fake-console", ["no-leader"], "message")
    hidden = action_guard.reserve(4, "other-console", ["other-rule"], "message")
    assert invoke("get_pending_automod_actions", "GET", set()).status_code == 403
    response = invoke("get_pending_automod_actions", "GET", {"api.can_view_player_profile"})
    result = json.loads(response.content)["result"]["results"]
    assert [row["token"] for row in result] == [token]
    body = {"player_id": "fake-console", "token": token, "reason": "checked server log"}
    assert invoke("review_pending_automod_action", "POST", {"api.can_view_player_profile"}, body).status_code == 403
    response = invoke("review_pending_automod_action", "POST", {"api.can_view_player_profile", "api.can_run_raw_commands"}, body)
    assert response.status_code == 200 and json.loads(response.content)["result"] is True
    body.update(player_id="other-console", token=hidden)
    response = invoke("review_pending_automod_action", "POST", {"api.can_view_player_profile", "api.can_run_raw_commands"}, body)
    assert response.status_code == 200 and json.loads(response.content)["result"] is False
    with guard_api() as session:
        row = session.execute(select(action_guard.action_guard_history).where(
            action_guard.action_guard_history.c.token == token,
            action_guard.action_guard_history.c.event == "reviewed")).mappings().one()
        assert (row["actor"], row["reason"]) == ("Operator", "checked server log")
