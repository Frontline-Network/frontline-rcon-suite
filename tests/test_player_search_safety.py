from contextlib import contextmanager
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Query, Session

from rcon import player_history
from rcon.models import PlayerID, PlayerName, PlayerSession, PlayerAccount, PlayerVIP, SteamInfo


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
    return engine


def test_alias_without_account_is_found_and_not_counted_twice(database):
    now = datetime.now()
    with Session(database) as sess:
        player = PlayerID(player_id="console-id", created=now)
        sess.add(player)
        sess.flush()
        for name in ("Example one", "Example two"):
            sess.add(PlayerName(player_id_id=player.id, name=name, created=now, last_seen=now))
        sess.commit()
    result = player_history.get_players_by_appearance(player_name="Example", ignore_accent=False, page_size=1)
    assert result["total"] == 1
    assert [player["player_id"] for player in result["players"]] == ["console-id"]


def test_country_matches_either_optional_profile(database):
    now = datetime.now()
    with Session(database) as sess:
        player = PlayerID(player_id="steam-id", created=now)
        sess.add(player)
        sess.flush()
        sess.add(PlayerAccount(player_id_id=player.id, country="FR"))
        sess.add(SteamInfo(player_id_id=player.id, country="DE", profile={}, bans={}, updated=now))
        sess.commit()
    for country in ("DE", "FR"):
        result = player_history.get_players_by_appearance(country=country)
        assert result["total"] == 1
        assert result["players"][0]["player_id"] == "steam-id"


def test_account_name_and_country_work_without_soldier_or_steam_profile(database):
    with Session(database) as sess:
        player = PlayerID(player_id="account-only", created=datetime.now())
        sess.add(player)
        sess.flush()
        sess.add(PlayerAccount(player_id_id=player.id, name="AccountName", country="FR"))
        sess.commit()
    result = player_history.get_players_by_appearance(player_name="AccountName", country="FR", ignore_accent=False)
    assert result["total"] == 1
    assert result["players"][0]["player_id"] == "account-only"


def test_page_loads_vips_once_and_returns_local_expiration(database, monkeypatch):
    from sqlalchemy import event

    monkeypatch.setenv("SERVER_NUMBER", "3")
    expires = datetime(2030, 1, 1)
    with Session(database) as sess:
        local = PlayerID(player_id="local")
        remote = PlayerID(player_id="remote")
        sess.add_all([local, remote])
        sess.flush()
        sess.add_all([PlayerVIP(player_id_id=player.id, server_number=server, expiration=expires)
                      for player, server in ((local, 3), (local, 4), (remote, 4))])
        sess.commit()

    vip_queries = []

    @event.listens_for(database, "before_cursor_execute")
    def record_vip_query(_conn, _cursor, statement, *_args):
        if "FROM player_vip" in statement:
            vip_queries.append(statement)

    def profile(player, *, limit_sessions, preloaded_vips):
        return {"player_id": player.player_id, "servers": sorted(v.server_number for v in preloaded_vips)}

    monkeypatch.setattr(PlayerID, "to_dict", profile)
    result = player_history.get_players_by_appearance(page_size=2)
    assert result["total"] == 2
    assert len(vip_queries) == 1
    assert {p["player_id"]: (p["servers"], p["vip_expiration"]) for p in result["players"]} == {
        "local": ([3, 4], expires), "remote": ([4], None),
    }
