"""Last-seen filters use confirmed current players, never stale open sessions."""
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
import os
import time
from types import SimpleNamespace
from unittest.mock import Mock
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Query, Session
from sqlalchemy.schema import CreateSchema, DropSchema

from rcon import api_commands, player_history
from rcon.player_presence import PresenceWindow
from rcon.models import PlayerAccount, PlayerID, PlayerName, PlayerSession, PlayerVIP, SteamInfo


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_element, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite://")
    for model in (PlayerID, PlayerName, PlayerSession, PlayerAccount, PlayerVIP, SteamInfo):
        model.__table__.create(engine)
    @contextmanager
    def session():
        with Session(engine) as sess:
            yield sess
    monkeypatch.setattr(player_history, "enter_session", session)
    monkeypatch.setattr(Query, "options", lambda self, *args, **kwargs: self)
    monkeypatch.setattr(PlayerID, "to_dict", lambda self, **kwargs: {"player_id": self.player_id})
    monkeypatch.setattr(player_history, "get_player_identity_links", lambda sess, players: {p.player_id: {} for p in players})
    now = datetime(2026, 11, 16, 12)
    with Session(engine) as sess:
        for pid, server in [("console-online", 3), ("stale-open", 3), ("other-server-open", 4)]:
            player = PlayerID(player_id=pid, created=now - timedelta(hours=4))
            sess.add(player)
            sess.flush()
            sess.add(PlayerSession(player_id_id=player.id, start=now - timedelta(hours=3),
                                   created=now - timedelta(hours=3), end=None,
                                   server_number=server, server_name="synthetic"))
        sess.commit()
    yield engine
    engine.dispose()


def test_only_verified_online_player_matches_recent_filter(database):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    result = player_history.get_players_by_appearance(
        last_seen_from=now - timedelta(hours=1), online_now_ids={"console-online"}, observed_at=now)
    assert result["total"] == 1
    assert result["local_online_snapshot_available"] is True
    assert result["players"][0]["player_id"] == "console-online"
    assert result["players"][0]["last_seen_timestamp_ms"] == int(now.timestamp() * 1000)


def test_old_filter_and_pagination_use_the_same_verified_timestamp(database):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    old = player_history.get_players_by_appearance(
        last_seen_till=now - timedelta(hours=1), online_now_ids={"console-online"}, observed_at=now)
    assert {p["player_id"] for p in old["players"]} == {"stale-open", "other-server-open"}
    first = player_history.get_players_by_appearance(page_size=1, online_now_ids={"console-online"}, observed_at=now)
    assert first["players"][0]["player_id"] == "console-online"


def test_unavailable_snapshot_does_not_invent_online_presence(database):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    result = player_history.get_players_by_appearance(last_seen_from=now - timedelta(hours=1),
                                                       online_now_ids=None, observed_at=now)
    assert result["total"] == 0
    assert result["local_online_snapshot_available"] is False


def test_confirmed_other_server_observation_updates_filters_and_sorting(database):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    remote = {'other-server-open': PresenceWindow(now.timestamp() - 20, now.timestamp() - 18)}
    result = player_history.get_players_by_appearance(
        last_seen_from=now - timedelta(minutes=1), online_now_ids=set(),
        observed_at=now, remote_observations=remote)
    assert [p['player_id'] for p in result['players']] == ['other-server-open']
    assert result['players'][0]['last_seen_timestamp_ms'] == int((now.timestamp() - 20) * 1000)
    assert result['players'][0]['last_seen_observation_window_ms'] == [
        int((now.timestamp() - 20) * 1000), int((now.timestamp() - 18) * 1000)]
    old = player_history.get_players_by_appearance(
        last_seen_till=now - timedelta(minutes=1), online_now_ids=set(),
        observed_at=now, remote_observations=remote)
    assert {p['player_id'] for p in old['players']} == {'console-online', 'stale-open'}
    first = player_history.get_players_by_appearance(
        page_size=1, online_now_ids=set(), observed_at=now, remote_observations=remote)
    assert first['players'][0]['player_id'] == 'other-server-open'


def test_filter_boundary_inside_observation_window_is_not_treated_as_exact(database):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    remote = {'other-server-open': PresenceWindow(now.timestamp() - 20, now.timestamp() - 10)}
    bound = now - timedelta(seconds=15)
    recent = player_history.get_players_by_appearance(
        last_seen_from=bound, online_now_ids=set(), observed_at=now, remote_observations=remote)
    older = player_history.get_players_by_appearance(
        last_seen_till=bound, online_now_ids=set(), observed_at=now, remote_observations=remote)
    assert 'other-server-open' not in {p['player_id'] for p in recent['players']}
    assert 'other-server-open' not in {p['player_id'] for p in older['players']}


def test_local_and_later_remote_sightings_do_not_override_each_other(database):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    remote = {'console-online': PresenceWindow(now.timestamp() + 1, now.timestamp() + 2)}
    later = now + timedelta(milliseconds=500)
    recent = player_history.get_players_by_appearance(
        last_seen_from=later, online_now_ids={'console-online'}, observed_at=now,
        remote_observations=remote)
    assert [p['player_id'] for p in recent['players']] == ['console-online']
    assert recent['players'][0]['last_seen_timestamp_ms'] == int((now.timestamp() + 1) * 1000)
    assert recent['players'][0]['last_seen_observation_window_ms'] == [
        int((now.timestamp() + 1) * 1000), int((now.timestamp() + 2) * 1000)]
    older = player_history.get_players_by_appearance(
        last_seen_till=now + timedelta(milliseconds=1500), online_now_ids={'console-online'},
        observed_at=now, remote_observations=remote)
    assert 'console-online' not in {p['player_id'] for p in older['players']}


@pytest.mark.skipif(not hasattr(time, 'tzset'), reason='requires controllable local timezone')
def test_remote_sighting_across_daylight_saving_fold(database, monkeypatch):
    # The later instant has an earlier wall-clock representation after the fold.
    later = datetime(2026, 10, 25, 1, 0, 1, tzinfo=timezone.utc)
    remote = {'other-server-open': PresenceWindow(later.timestamp(), later.timestamp() + 2)}
    try:
        with monkeypatch.context() as scope:
            scope.setenv('TZ', 'Europe/Berlin')
            time.tzset()
            with Session(database) as sess:
                player = sess.query(PlayerID).filter_by(player_id='other-server-open').one()
                session = sess.query(PlayerSession).filter_by(player_id_id=player.id).one()
                session.created = datetime(2026, 10, 25, 2, 59, 58)
                session.end = datetime(2026, 10, 25, 2, 59, 58)
                session.end_event_us = int(datetime(2026, 10, 25, 0, 59, 58, tzinfo=timezone.utc).timestamp() * 1_000_000)
                sess.commit()
            result = player_history.get_players_by_appearance(
                player_id='other-server-open', online_now_ids=set(),
                observed_at=later + timedelta(seconds=3), remote_observations=remote)
            assert result['players'][0]['last_seen_timestamp_ms'] == int(later.timestamp() * 1000)
            assert result['players'][0]['last_seen_observation_window_ms'] is not None
    finally:
        time.tzset()


@pytest.mark.skipif(not hasattr(time, 'tzset'), reason='requires controllable local timezone')
def test_verified_disconnect_after_earlier_remote_sighting_across_fold(database, monkeypatch):
    earlier = datetime(2026, 10, 25, 0, 59, 58, tzinfo=timezone.utc)
    later = datetime(2026, 10, 25, 1, 0, 1, tzinfo=timezone.utc)
    remote = {'other-server-open': PresenceWindow(earlier.timestamp(), earlier.timestamp() + 2)}
    try:
        with monkeypatch.context() as scope:
            scope.setenv('TZ', 'Europe/Berlin')
            time.tzset()
            with Session(database) as sess:
                player = sess.query(PlayerID).filter_by(player_id='other-server-open').one()
                session = sess.query(PlayerSession).filter_by(player_id_id=player.id).one()
                session.created = datetime(2026, 10, 25, 2, 0, 1)
                session.end = datetime(2026, 10, 25, 2, 0, 1)
                session.end_event_us = int(later.timestamp() * 1_000_000)
                sess.commit()
            result = player_history.get_players_by_appearance(
                player_id='other-server-open', online_now_ids=set(),
                observed_at=later + timedelta(seconds=3), remote_observations=remote)
            assert result['players'][0]['last_seen_timestamp_ms'] == int(later.timestamp() * 1000)
            assert result['players'][0]['last_seen_observation_window_ms'] is None
    finally:
        time.tzset()


@pytest.mark.skipif(not hasattr(time, 'tzset'), reason='requires controllable local timezone')
def test_remote_sorting_across_daylight_saving_fold(database, monkeypatch):
    earlier = datetime(2026, 10, 25, 0, 59, 58, tzinfo=timezone.utc)
    later = datetime(2026, 10, 25, 1, 0, 1, tzinfo=timezone.utc)
    remote = {
        'stale-open': PresenceWindow(earlier.timestamp(), earlier.timestamp()),
        'other-server-open': PresenceWindow(later.timestamp(), later.timestamp()),
    }
    try:
        with monkeypatch.context() as scope:
            scope.setenv('TZ', 'Europe/Berlin')
            time.tzset()
            with Session(database) as sess:
                for session in sess.query(PlayerSession):
                    session.created = datetime(2026, 10, 24, 12)
                sess.commit()
            result = player_history.get_players_by_appearance(
                online_now_ids=set(), observed_at=later + timedelta(seconds=3),
                remote_observations=remote, page_size=1)
            assert result['players'][0]['player_id'] == 'other-server-open'
    finally:
        time.tzset()


@pytest.mark.skipif(not hasattr(time, 'tzset'), reason='requires controllable local timezone')
def test_verified_historical_filter_across_daylight_saving_fold(database, monkeypatch):
    old = datetime(2026, 10, 25, 0, 59, 58, tzinfo=timezone.utc)
    cutoff = datetime(2026, 10, 25, 1, 0, 0, tzinfo=timezone.utc)
    try:
        with monkeypatch.context() as scope:
            scope.setenv('TZ', 'Europe/Berlin')
            time.tzset()
            with Session(database) as sess:
                player = sess.query(PlayerID).filter_by(player_id='other-server-open').one()
                session = sess.query(PlayerSession).filter_by(player_id_id=player.id).one()
                session.created = datetime(2026, 10, 25, 2, 59, 58)
                session.end = datetime(2026, 10, 25, 2, 59, 58)
                session.end_event_us = int(old.timestamp() * 1_000_000)
                sess.commit()
            recent = player_history.get_players_by_appearance(
                player_id='other-server-open', last_seen_from=cutoff, online_now_ids=set(),
                observed_at=cutoff + timedelta(seconds=3))
            older = player_history.get_players_by_appearance(
                player_id='other-server-open', last_seen_till=cutoff, online_now_ids=set(),
                observed_at=cutoff + timedelta(seconds=3))
            assert recent['total'] == 0
            assert older['total'] == 1
    finally:
        time.tzset()


@pytest.mark.skipif(not hasattr(time, 'tzset'), reason='requires controllable local timezone')
def test_verified_history_and_remote_sort_by_absolute_instant_across_fold(database, monkeypatch):
    old = datetime(2026, 10, 25, 0, 59, 58, tzinfo=timezone.utc)
    new = datetime(2026, 10, 25, 1, 0, 1, tzinfo=timezone.utc)
    remote = {'other-server-open': PresenceWindow(new.timestamp(), new.timestamp())}
    try:
        with monkeypatch.context() as scope:
            scope.setenv('TZ', 'Europe/Berlin')
            time.tzset()
            with Session(database) as sess:
                for session in sess.query(PlayerSession):
                    session.created = datetime(2026, 10, 24, 12)
                player = sess.query(PlayerID).filter_by(player_id='stale-open').one()
                session = sess.query(PlayerSession).filter_by(player_id_id=player.id).one()
                session.end = datetime(2026, 10, 25, 2, 59, 58)
                session.end_event_us = int(old.timestamp() * 1_000_000)
                sess.commit()
            result = player_history.get_players_by_appearance(
                online_now_ids=set(), observed_at=new + timedelta(seconds=3),
                remote_observations=remote, page_size=1)
            assert result['players'][0]['player_id'] == 'other-server-open'
    finally:
        time.tzset()


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="requires controllable local timezone")
def test_offset_filters_keep_legacy_history_semantics_in_non_utc_process(database, monkeypatch):
    now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
    try:
        with monkeypatch.context() as scope:
            scope.setenv("TZ", "Europe/Berlin")
            time.tzset()
            threshold = datetime(2026, 11, 16, 12, 30, tzinfo=timezone(timedelta(hours=1)))
            recent = player_history.get_players_by_appearance(last_seen_from=threshold,
                online_now_ids={"console-online"}, observed_at=now)
            assert [p["player_id"] for p in recent["players"]] == ["console-online"]
            old = player_history.get_players_by_appearance(last_seen_till=threshold,
                online_now_ids={"console-online"}, observed_at=now)
            assert {p["player_id"] for p in old["players"]} == {"stale-open", "other-server-open"}
    finally:
        time.tzset()


def test_api_passes_full_console_ids_and_handles_snapshot_failure(monkeypatch):
    search = Mock(return_value={"total": 0, "players": []})
    monkeypatch.setattr(api_commands, "get_players_by_appearance", search)
    api = SimpleNamespace(get_player_ids=Mock(return_value=[("Same", "console-1"), ("Same", "console-2")]),
                          without_retries=nullcontext)
    api_commands.RconAPI.get_players_history(api)
    assert search.call_args.kwargs["online_now_ids"] == {"console-1", "console-2"}
    api.get_player_ids.side_effect = OSError("synthetic outage")
    api_commands.RconAPI.get_players_history(api)
    assert search.call_args.kwargs["online_now_ids"] is None
    api.get_player_ids.side_effect = None
    api.get_player_ids.return_value = [("Valid", "console-1"), ("Invalid", None)]
    api_commands.RconAPI.get_players_history(api)
    assert search.call_args.kwargs["online_now_ids"] is None
    api.get_player_ids.return_value = [("One", "console-1"), ("Two", "console-1")]
    api_commands.RconAPI.get_players_history(api)
    assert search.call_args.kwargs["online_now_ids"] is None


def test_api_uses_remote_observations_and_falls_back_when_unavailable(monkeypatch):
    from rcon import player_presence

    monkeypatch.setattr(api_commands, 'get_server_number', lambda: '3')
    search = Mock(return_value={'total': 0, 'players': []})
    monkeypatch.setattr(api_commands, 'get_players_by_appearance', search)
    remote = {'synthetic': PresenceWindow(100, 101)}
    reader = Mock(return_value=(remote, {4}))
    monkeypatch.setattr(player_presence, 'read_other_servers', reader)
    api = SimpleNamespace(get_player_ids=Mock(return_value=[]), without_retries=nullcontext)
    api_commands.RconAPI.get_players_history(api)
    reader.assert_called_once_with(3)
    assert search.call_args.kwargs['remote_observations'] == remote
    reader.side_effect = OSError('synthetic outage')
    api_commands.RconAPI.get_players_history(api)
    assert search.call_args.kwargs['remote_observations'] == {}


def exercise_real_cross_server_pipeline(monkeypatch, player_id):
    import redis
    from rcon import cache_utils, player_presence

    red = redis.Redis.from_url(os.environ['TEST_REDIS_URL'])
    database_url = 'postgresql://synthetic@localhost/presence_' + uuid.uuid4().hex
    scope = player_presence.database_scope(database_url)
    key = player_presence.snapshot_key(scope, 4)
    monkeypatch.setenv('HLL_DB_URL', database_url)
    monkeypatch.setattr(cache_utils, 'get_redis_client', lambda **kwargs: red)
    monkeypatch.setattr(api_commands, 'get_server_number', lambda: '3')
    source = SimpleNamespace(get_player_ids=lambda: [('Synthetic', player_id)],
                             without_retries=nullcontext)
    local = SimpleNamespace(get_player_ids=lambda: [], without_retries=nullcontext)
    try:
        assert player_presence.capture_observation(red, source, scope=scope, server_number=4)
        result = api_commands.RconAPI.get_players_history(
            local, last_seen_from=datetime.now(timezone.utc) - timedelta(minutes=1))
        assert [player['player_id'] for player in result['players']] == [player_id]
        assert result['players'][0]['last_seen_observation_window_ms'] is not None
        red.delete(key)
        result = api_commands.RconAPI.get_players_history(
            local, last_seen_from=datetime.now(timezone.utc) - timedelta(minutes=1))
        assert result['total'] == 0
    finally:
        red.delete(key)
        red.close()


@pytest.mark.skipif(not os.environ.get('TEST_REDIS_URL'), reason='requires isolated Redis')
def test_real_remote_roster_to_api_search(database, monkeypatch):
    exercise_real_cross_server_pipeline(monkeypatch, 'other-server-open')


@pytest.mark.skipif(not os.environ.get("RCON_SEARCH_TEST_DATABASE"), reason="requires isolated PostgreSQL")
def test_postgres_filters_order_and_console_ids_with_utc_offsets(monkeypatch):
    base = create_engine(os.environ["RCON_SEARCH_TEST_DATABASE"])
    schema = "player_seen_" + uuid.uuid4().hex
    with base.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = base.execution_options(schema_translate_map={None: schema})
    try:
        for model in (PlayerID, PlayerName, PlayerSession, PlayerAccount, PlayerVIP, SteamInfo):
            model.__table__.create(engine)
        @contextmanager
        def session():
            with Session(engine) as sess:
                yield sess
        monkeypatch.setattr(player_history, "enter_session", session)
        monkeypatch.setattr(Query, "options", lambda self, *args, **kwargs: self)
        monkeypatch.setattr(PlayerID, "to_dict", lambda self, **kwargs: {"player_id": self.player_id})
        monkeypatch.setattr(player_history, "get_player_identity_links", lambda sess, players: {p.player_id: {} for p in players})
        now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc)
        with Session(engine) as sess:
            for pid, server in [("console-online", 3), ("orphan-other-server", 4)]:
                player = PlayerID(player_id=pid, created=datetime(2026, 11, 16, 8))
                sess.add(player)
                sess.flush()
                sess.add(PlayerSession(player_id_id=player.id, start=datetime(2026, 11, 16, 9),
                                       created=datetime(2026, 11, 16, 9), end=None,
                                       server_number=server, server_name="synthetic"))
            sess.commit()
        if os.environ.get('TEST_REDIS_URL'):
            exercise_real_cross_server_pipeline(monkeypatch, 'orphan-other-server')
        threshold = datetime(2026, 11, 16, 12, 30, tzinfo=timezone(timedelta(hours=1)))
        result = player_history.get_players_by_appearance(last_seen_from=threshold,
            online_now_ids={"console-online"}, observed_at=now, page_size=1)
        assert result["total"] == 1 and result["players"][0]["player_id"] == "console-online"
        assert result["players"][0]["last_seen_timestamp_ms"] == int(now.timestamp() * 1000)
        remote = {'orphan-other-server': PresenceWindow(now.timestamp() - 20, now.timestamp() - 18)}
        result = player_history.get_players_by_appearance(last_seen_from=now - timedelta(minutes=1),
            online_now_ids=set(), observed_at=now, remote_observations=remote, page_size=1)
        assert result['total'] == 1 and result['players'][0]['player_id'] == 'orphan-other-server'
        assert result['players'][0]['last_seen_timestamp_ms'] == int((now.timestamp() - 20) * 1000)
        # Maximum validated population across 31 other servers, with one
        # observation window per server. Exercise count, filters and ordering.
        large_remote = {
            f'synthetic-{server}-{index}': PresenceWindow(now.timestamp() - server / 10,
                                                          now.timestamp() - server / 10)
            for server in range(1, 32) for index in range(250)
        }
        del large_remote['synthetic-1-0']
        large_remote['orphan-other-server'] = PresenceWindow(now.timestamp() - 1, now.timestamp() - 1)
        result = player_history.get_players_by_appearance(
            player_id='orphan-other-server', last_seen_from=now - timedelta(minutes=1),
            last_seen_till=now + timedelta(minutes=1), online_now_ids=set(),
            observed_at=now, remote_observations=large_remote, page_size=1)
        assert result['total'] == 1
        assert result['players'][0]['last_seen_timestamp_ms'] == int((now.timestamp() - 1) * 1000)
        if hasattr(time, 'tzset'):
            old = datetime(2026, 10, 25, 0, 59, 58, tzinfo=timezone.utc)
            new = datetime(2026, 10, 25, 1, 0, 1, tzinfo=timezone.utc)
            try:
                with monkeypatch.context() as scope:
                    scope.setenv('TZ', 'Europe/Berlin')
                    time.tzset()
                    with Session(engine) as sess:
                        for record in sess.query(PlayerSession):
                            record.created = datetime(2026, 10, 24, 12)
                        player = sess.query(PlayerID).filter_by(player_id='console-online').one()
                        record = sess.query(PlayerSession).filter_by(player_id_id=player.id).one()
                        record.end = datetime(2026, 10, 25, 2, 59, 58)
                        record.end_event_us = int(old.timestamp() * 1_000_000)
                        sess.commit()
                    remote = {'orphan-other-server': PresenceWindow(new.timestamp(), new.timestamp())}
                    result = player_history.get_players_by_appearance(
                        online_now_ids=set(), observed_at=new + timedelta(seconds=3),
                        remote_observations=remote, page_size=1)
                    assert result['players'][0]['player_id'] == 'orphan-other-server'
                    recent = player_history.get_players_by_appearance(
                        player_id='console-online', last_seen_from=new,
                        online_now_ids=set(), observed_at=new + timedelta(seconds=3))
                    assert recent['total'] == 0
            finally:
                time.tzset()
    finally:
        with base.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        base.dispose()
