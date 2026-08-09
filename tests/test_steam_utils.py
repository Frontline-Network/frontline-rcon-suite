import pytest

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
