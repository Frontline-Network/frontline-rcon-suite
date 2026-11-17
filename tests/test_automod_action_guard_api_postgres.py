"""Guard review is restricted to authorized operators and the active server."""
import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from tests.test_session_event_api_postgres import invoke
from rcon.automods import action_guard, tk_action_guard


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
    action_guard.event_guard.metadata.create_all(engine)
    tk_action_guard.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(action_guard, "get_session_maker", lambda: maker)
    monkeypatch.setattr(action_guard.event_guard, "get_session_maker", lambda: maker)
    monkeypatch.setattr(tk_action_guard, "get_session_maker", lambda: maker)
    monkeypatch.setattr(tk_action_guard, "_transition_boundary", lambda event: event)
    monkeypatch.setattr("rcon.api_commands.get_server_number", lambda: "3")
    try:
        yield maker
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def test_review_endpoint_accepts_real_query_string_limit(guard_api):
    action_guard.reserve(3, 'synthetic-one', ['no-leader'], 'message')
    action_guard.reserve(3, 'synthetic-two', ['no-leader'], 'message')
    response = invoke('get_pending_automod_actions', 'GET',
                      {'api.can_view_player_profile'}, {'limit': '1'})
    assert response.status_code == 200
    result = json.loads(response.content)['result']
    assert len(result['results']) == 1
    assert result['more'] is True


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


def test_teamkill_pending_is_visible_and_review_is_audited(guard_api):
    # The initial observation establishes the safe transition boundary.
    assert tk_action_guard.reserve(3, "old-session", 1000, 2000) is None
    token = tk_action_guard.reserve(3, "console-player", 3000, 4000)
    assert token
    response = invoke("get_pending_automod_actions", "GET", {"api.can_view_player_profile"})
    rows = json.loads(response.content)["result"]["results"]
    assert any(row["token"] == token and row["actions"][0]["action"] == "ban" for row in rows)
    body = {"player_id": "console-player", "token": token, "reason": "verified outcome"}
    assert invoke("review_pending_automod_action", "POST", {"api.can_view_player_profile"}, body).status_code == 403
    response = invoke("review_pending_automod_action", "POST", {"api.can_view_player_profile", "api.can_run_raw_commands"}, body)
    assert response.status_code == 200 and json.loads(response.content)["result"] is True
    with guard_api() as session:
        row = session.execute(select(tk_action_guard.history).where(
            tk_action_guard.history.c.token == token,
            tk_action_guard.history.c.event == "reviewed")).mappings().one()
        assert (row["actor"], row["reason"]) == ("Operator", "verified outcome")


def test_event_action_review_blocks_replay_but_allows_new_event(guard_api):
    now = int(datetime.now(timezone.utc).timestamp() * 1000)
    event_guard = action_guard.event_guard
    with guard_api.begin() as session:
        session.execute(event_guard.cutover.insert().values(server_number=3, boundary_ms=now - 1000, cleanup_ms=now))
    event = event_guard.identity({'timestamp_ms': now, 'line_without_time': 'KILL: synthetic'})
    token = action_guard.reserve(3, 'synthetic', ['AutoMod_SeedingRules'], 'punish', event=event)
    response = invoke('get_pending_automod_actions', 'GET', {'api.can_view_player_profile'})
    assert any(row['token'] == token for row in json.loads(response.content)['result']['results'])
    body = {'player_id': 'synthetic', 'token': token, 'reason': 'checked outcome'}
    assert invoke('review_pending_automod_action', 'POST', {'api.can_view_player_profile'}, body).status_code == 403
    response = invoke('review_pending_automod_action', 'POST', {'api.can_view_player_profile', 'api.can_run_raw_commands'}, body)
    assert response.status_code == 200 and json.loads(response.content)['result'] is True
    assert action_guard.reserve(3, 'synthetic', ['AutoMod_SeedingRules'], 'punish', event=event) is None
    next_event = event_guard.identity({'timestamp_ms': now, 'line_without_time': 'KILL: another'})
    assert action_guard.reserve(3, 'synthetic', ['AutoMod_SeedingRules'], 'punish', event=next_event)


def test_uncertain_autobalancer_switch_requires_audited_review(guard_api):
    token = action_guard.reserve(3, 'synthetic', ['AutobalancerSwitch'], 'switch')
    response = invoke('get_pending_automod_actions', 'GET', {'api.can_view_player_profile'})
    rows = json.loads(response.content)['result']['results']
    assert any(row['token'] == token and row['actions'][0]['action'] == 'switch' for row in rows)
    body = {'player_id': 'synthetic', 'token': token, 'reason': 'checked server logs'}
    assert invoke('review_pending_automod_action', 'POST', {'api.can_view_player_profile'}, body).status_code == 403
    response = invoke('review_pending_automod_action', 'POST',
                      {'api.can_view_player_profile', 'api.can_run_raw_commands'}, body)
    assert response.status_code == 200 and json.loads(response.content)['result'] is True
    assert action_guard.pending_players(3, 'AutobalancerSwitch') == set()
    with guard_api() as session:
        events = session.execute(select(action_guard.action_guard_history).where(
            action_guard.action_guard_history.c.token == token)).mappings().all()
    assert any(row['event'] == 'reviewed' and row['actor'] == 'Operator' and
               row['reason'] == 'checked server logs' for row in events)


def test_uncertain_vac_ban_requires_audited_review(guard_api):
    token = action_guard.reserve(3, 'synthetic', ['VacHistory'], 'ban')
    response = invoke('get_pending_automod_actions', 'GET', {'api.can_view_player_profile'})
    rows = json.loads(response.content)['result']['results']
    assert any(row['token'] == token and row['actions'][0] == {'rule': 'VacHistory', 'action': 'ban'} for row in rows)
    body = {'player_id': 'synthetic', 'token': token, 'reason': 'checked server logs'}
    assert invoke('review_pending_automod_action', 'POST', {'api.can_view_player_profile'}, body).status_code == 403
    response = invoke('review_pending_automod_action', 'POST',
                      {'api.can_view_player_profile', 'api.can_run_raw_commands'}, body)
    assert response.status_code == 200 and json.loads(response.content)['result'] is True
    assert action_guard.pending_players(3, 'VacHistory') == set()
    with guard_api() as session:
        events = session.execute(select(action_guard.action_guard_history).where(
            action_guard.action_guard_history.c.token == token)).mappings().all()
    assert any(row['event'] == 'reviewed' and row['actor'] == 'Operator' and
               row['reason'] == 'checked server logs' for row in events)


def test_uncertain_blacklist_action_requires_audited_review(guard_api):
    token = action_guard.reserve(3, 'synthetic', ['BlacklistEnforcement'], 'ban')
    response = invoke('get_pending_automod_actions', 'GET', {'api.can_view_player_profile'})
    rows = json.loads(response.content)['result']['results']
    assert any(row['token'] == token and row['actions'][0] == {'rule': 'BlacklistEnforcement', 'action': 'ban'} for row in rows)
    body = {'player_id': 'synthetic', 'token': token, 'reason': 'checked server logs'}
    assert invoke('review_pending_automod_action', 'POST', {'api.can_view_player_profile'}, body).status_code == 403
    response = invoke('review_pending_automod_action', 'POST',
                      {'api.can_view_player_profile', 'api.can_run_raw_commands'}, body)
    assert response.status_code == 200 and json.loads(response.content)['result'] is True
    assert action_guard.pending_players(3, 'BlacklistEnforcement') == set()
    with guard_api() as session:
        events = session.execute(select(action_guard.action_guard_history).where(
            action_guard.action_guard_history.c.token == token)).mappings().all()
    assert any(row['event'] == 'reviewed' and row['actor'] == 'Operator' and
               row['reason'] == 'checked server logs' for row in events)
