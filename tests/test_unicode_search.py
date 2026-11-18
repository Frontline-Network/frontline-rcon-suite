"""Unicode-preserving player and blacklist search regressions."""
from contextlib import contextmanager
from datetime import datetime
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Query, Session

from rcon import player_history
from rcon.blacklist import search_blacklist_records
from rcon.models import Blacklist, BlacklistRecord, PlayerAccount, PlayerID, PlayerName, PlayerSession, PlayerVIP, SteamInfo


@compiles(JSONB, "sqlite")
def jsonb_sqlite(_element, _compiler, **_kwargs):
    return "JSON"


@pytest.fixture(params=["sqlite", "postgres"])
def database(monkeypatch, request):
    root = None
    schema = None
    if request.param == "postgres":
        dsn = os.environ.get("TEST_POSTGRES_DSN")
        if not dsn:
            pytest.skip("requires disposable PostgreSQL")
        root = create_engine(dsn)
        schema = "unicode_search_" + uuid4().hex
        with root.begin() as conn:
            conn.exec_driver_sql("CREATE EXTENSION IF NOT EXISTS unaccent WITH SCHEMA public")
            conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema},public"})
    else:
        engine = create_engine("sqlite://")
        @event.listens_for(engine, "connect")
        def unaccent(connection, _):
            connection.create_function("unaccent", 1, lambda text: player_history.remove_accent(text) if text else text)
    for model in (PlayerID, PlayerName, PlayerSession, PlayerAccount, PlayerVIP, SteamInfo, Blacklist, BlacklistRecord):
        model.__table__.create(engine)
    @contextmanager
    def session():
        with Session(engine) as sess:
            yield sess
    monkeypatch.setattr(player_history, "enter_session", session)
    monkeypatch.setattr(Query, "options", lambda self, *_args, **_kwargs: self)
    monkeypatch.setattr(PlayerID, "to_dict", lambda self, **_kwargs: {"player_id": self.player_id})
    monkeypatch.setattr(player_history, "get_player_identity_links", lambda _sess, players: {p.player_id: {} for p in players})
    with Session(engine) as sess:
        blacklist = Blacklist(name="fake")
        sess.add(blacklist)
        for ident, alias, account, reason in [
            ("a", "Alpha", "Élodie", "Règle reason"),
            ("b", "玩家Émile", "Other", "玩家违规"),
            ("c", "Straße", "Else", "Different reason"),
        ]:
            player = PlayerID(player_id=ident, created=datetime.now())
            sess.add(player)
            sess.flush()
            sess.add(PlayerAccount(player_id_id=player.id, name=account))
            sess.add(PlayerName(player_id_id=player.id, name=alias, created=datetime.now(), last_seen=datetime.now()))
            sess.add(BlacklistRecord(player_id_id=player.id, blacklist=blacklist, reason=reason, admin_name="fake"))
        sess.commit()
    yield engine
    engine.dispose()
    if root is not None:
        with root.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        root.dispose()


@pytest.mark.parametrize("search,expected", [("玩家", {"b"}), ("玩家Émile", {"b"}),
                                             ("Elodie", {"a"}), ("Élodie", {"a"}),
                                             ("E\u0301lodie", {"a"}), ("missing", set())])
def test_player_search_preserves_scripts_and_normalizes_account(database, search, expected):
    result = player_history.get_players_by_appearance(player_name=search, ignore_accent=True)
    assert {item["player_id"] for item in result["players"]} == expected
    assert result["total"] == len(expected)


def test_exact_name_and_empty_query_semantics(database):
    assert player_history.get_players_by_appearance(player_name="Élodie", exact_name_match=True)["total"] == 1
    assert player_history.get_players_by_appearance(player_name="Elodie", exact_name_match=True, ignore_accent=False)["total"] == 0
    assert player_history.get_players_by_appearance(player_name="", ignore_accent=True)["total"] == 3
    assert player_history.get_players_by_appearance(player_name="\u0301", ignore_accent=True)["total"] == 0


def test_blacklist_search_preserves_non_latin_terms(database):
    with Session(database) as sess:
        records, total = search_blacklist_records(sess, reason="玩家")
        assert total == 1
        assert records[0].player.player_id == "b"
        records, total = search_blacklist_records(sess, reason="Regle")
        assert total == 1 and records[0].player.player_id == "a"
        records, total = search_blacklist_records(sess, reason="\u0301")
        assert total == 0 and not records


def test_blacklist_pages_have_deterministic_order_when_timestamps_match(database):
    with Session(database) as sess:
        from rcon.models import BlacklistRecord
        records = sess.query(BlacklistRecord).all()
        for record in records:
            record.created_at = datetime(2020, 1, 1)
        sess.commit()
        expected = sorted((record.id for record in records), reverse=True)
        observed = []
        for page in range(1, len(records) + 1):
            result, total = search_blacklist_records(sess, page_size=1, page=page)
            assert total == len(records)
            observed.extend(record.id for record in result)
        assert observed == expected


def test_sort_normalization_does_not_drop_other_scripts():
    assert player_history.remove_accent("玩家Élodie") == "玩家Elodie"


def test_postgres_uses_same_transliteration_on_both_sides(database):
    if database.dialect.name != "postgresql":
        pytest.skip("PostgreSQL unaccent supplies transliteration rules")
    result = player_history.get_players_by_appearance(player_name="Strasse", ignore_accent=True)
    assert [item["player_id"] for item in result["players"]] == ["c"]
