from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from rcon import steam_utils
from rcon.steam_utils import (
    filter_steam_id,
    filter_steam_ids,
    is_steam_id_64,
    redact_steam_error,
)


@pytest.mark.parametrize(
    "id_, expected",
    [
        ("1", False),
        ("", False),
        ("a21af8b5-59df-5vbr-88gf-ab4239r4g6f4", False),
        ("76561198080212634", True),
    ],
)
def test_is_steam_id_64(id_, expected):
    assert is_steam_id_64(id_) == expected


@filter_steam_id()
def should_filter_single_id(player_id: str):
    return player_id


@filter_steam_ids()
def should_filter_multiple_ids(player_ids: list[str]):
    return player_ids


@pytest.mark.parametrize(
    "player_id, expected",
    [
        ("76561198080212634", "76561198080212634"),
        ("a21af8b5-59df-5vbr-88gf-ab4239r4g6f4", None),
    ],
)
def test_steam_id_filter(player_id, expected):
    assert should_filter_single_id(player_id) == expected


@pytest.mark.parametrize(
    "player_ids, expected",
    [
        (["76561198080212634"], ["76561198080212634"]),
        ([], []),
        (
            ["76561198080212634", "a21af8b5-59df-5vbr-88gf-ab4239r4g6f4"],
            ["76561198080212634"],
        ),
    ],
)
def test_steam_ids_filter(player_ids, expected: list[str]):
    assert should_filter_multiple_ids(player_ids) == expected


@pytest.mark.parametrize("parameter", ["key", "api_key", "apikey", "KEY"])
def test_redact_steam_error_hides_sensitive_query_parameters(parameter):
    secret = "do-not-log-this"
    message = (
        "429 for https://api.steampowered.com/example?"
        f"{parameter}={secret}&steamids=76561198080212634"
    )

    redacted = redact_steam_error(RuntimeError(message))

    assert secret not in redacted
    assert f"{parameter}=<redacted>" in redacted
    assert "steamids=76561198080212634" in redacted


def test_enrich_db_users_closes_each_page_before_throttling(monkeypatch):
    pages = [
        [
            SimpleNamespace(id=1, player_id="76561198000000001"),
            SimpleNamespace(id=2, player_id="76561198000000002"),
        ],
        [SimpleNamespace(id=3, player_id="76561198000000003")],
        [],
    ]
    events = []
    statements = []

    class FakeSession:
        def __init__(self, players):
            self.players = players

        def scalars(self, statement):
            statements.append(statement)
            return iter(self.players)

    sessions = [FakeSession(players) for players in pages]

    @contextmanager
    def fake_enter_session():
        index = len([event for event in events if event[0] == "enter"])
        events.append(("enter", index))
        try:
            yield sessions[index]
        finally:
            events.append(("exit", index))

    def fake_update_db_player_info(session, players):
        events.append(("update", tuple(player.id for player in players)))
        return len(players), len(players)

    monkeypatch.setattr(steam_utils, "enter_session", fake_enter_session)
    monkeypatch.setattr(
        steam_utils, "update_db_player_info", fake_update_db_player_info
    )
    monkeypatch.setattr(
        steam_utils.time, "sleep", lambda seconds: events.append(("sleep", seconds))
    )

    steam_utils.enrich_db_users(chunk_size=2)

    assert events == [
        ("enter", 0),
        ("update", (1, 2)),
        ("exit", 0),
        ("sleep", 1),
        ("enter", 1),
        ("update", (3,)),
        ("exit", 1),
        ("sleep", 1),
        ("enter", 2),
        ("exit", 2),
    ]
    assert [statement._limit_clause.value for statement in statements] == [2, 2, 2]
    assert [
        statement._where_criteria[0].right.value for statement in statements
    ] == [0, 2, 3]
    assert all("ORDER BY steam_id_64.id" in str(statement) for statement in statements)
