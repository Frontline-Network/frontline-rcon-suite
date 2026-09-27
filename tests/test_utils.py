from unittest import mock

import pytest

from rcon.game.hllv.maps import HLLV_LAYERS
from rcon.maps import LAYERS, Environment, GameMode, Team, UNKNOWN_MAP_NAME
from rcon.utils import FixedLenList, exception_in_chain, guess_map_from_log


class FakeException(Exception):
    pass


class ChainedException(Exception):
    pass


class DeepChainedException(Exception):
    pass


def test_guess_map_from_log_uses_game_specific_layers():
    layer = guess_map_from_log(
        {"raw": "MATCH START Cam Ranh Port Warfare"},
        HLLV_LAYERS,
    )

    assert layer.id == "wdeve_warfare_day"


@pytest.mark.parametrize("event", ["start", "end"])
@pytest.mark.parametrize("attacker,team", [("US", Team.ALLIES), ("NVA", Team.AXIS)])
def test_guess_map_from_log_van_tuong_offensive(event, attacker, team):
    title = f"VẠN TƯỜNG {attacker} Offensive"
    raw = (
        f"[749.511 ms (1790510209)] MATCH START {title}"
        if event == "start"
        else f"MATCH ENDED `{title}` ALLIED (3 - 2) AXIS"
    )
    layer = guess_map_from_log({"raw": raw}, HLLV_LAYERS)
    assert layer.id == f"wdeva_offensive{attacker.lower()}_day"
    assert layer.map.name == "VẠN TƯỜNG"
    assert layer.attackers == team


@pytest.mark.parametrize("layers", [LAYERS, HLLV_LAYERS], ids=["hll", "hllv"])
@pytest.mark.parametrize("event", ["start", "end"])
def test_guess_map_from_log_offensive_catalogue(layers, event):
    for expected in layers.values():
        if expected.game_mode != GameMode.OFFENSIVE or expected.attackers is None:
            continue
        faction = next(
            f
            for f in (expected.map.allies, expected.map.axis)
            if f.team == expected.attackers
        )
        title = (
            f"{expected.map.name} {faction.name} {expected.environment.value} Offensive"
        )
        raw = (
            f"MATCH START {title}"
            if event == "start"
            else f"MATCH ENDED `{title}` ALLIED (3 - 2) AXIS"
        )
        actual = guess_map_from_log({"raw": raw}, layers)
        # Different IDs may represent the same catalogue entry.
        assert actual.map == expected.map, raw
        assert actual.attackers == expected.attackers, raw
        assert actual.environment == expected.environment, raw
        assert actual.game_mode == expected.game_mode, raw


@pytest.mark.parametrize(
    "raw",
    [
        "MATCH START VẠN TƯỜNG GER Offensive",  # Not a faction on this map.
        "MATCH START VẠN TƯỜNG US Warfare",  # No faction suffix for other modes.
        "MATCH START Unknown Map US Offensive",
        "MATCH START VẠN TƯỜNG US Unsupported",
        "not a match log",
    ],
)
def test_guess_map_from_log_does_not_guess_invalid_factions_or_maps(raw):
    assert guess_map_from_log({"raw": raw}, HLLV_LAYERS).id == UNKNOWN_MAP_NAME


def test_guess_map_from_log_legacy_offensive_without_attacker():
    layer = guess_map_from_log({"raw": "MATCH START UTAH BEACH OFFENSIVE"})
    assert layer.map.name == "UTAH BEACH"
    assert layer.game_mode == GameMode.OFFENSIVE
    assert layer.environment == Environment.DAY


@pytest.mark.parametrize("layers", [LAYERS, HLLV_LAYERS], ids=["hll", "hllv"])
@pytest.mark.parametrize("event", ["start", "end"])
def test_guess_map_from_log_full_catalogue(layers, event):
    for expected in layers.values():
        if expected.id == UNKNOWN_MAP_NAME:
            continue
        title = f"{expected.map.name} {expected.environment.value} {expected.game_mode.value}"
        raw = (
            f"MATCH START {title}"
            if event == "start"
            else f"MATCH ENDED `{title}` ALLIED (3 - 2) AXIS"
        )
        actual = guess_map_from_log({"raw": raw}, layers)
        assert actual.map == expected.map, raw
        assert actual.game_mode == expected.game_mode, raw
        assert actual.environment == expected.environment, raw


@pytest.mark.parametrize(
    "title,expected",
    [
        ("QUẢNG NGÃI NVA Offensive", "wdevb_offensivenva_day"),
        ("CAM RANH PORT US Offensive", "wdeve_offensiveus_day"),
        ("CAM RANH PORT NVA Offensive", "wdeve_offensivenva_day"),
    ],
)
def test_guess_map_from_log_other_observed_offensive_failures(title, expected):
    assert (
        guess_map_from_log({"raw": f"MATCH START {title}"}, HLLV_LAYERS).id == expected
    )


def test_direct_exception():
    assert exception_in_chain(FakeException(), FakeException)


def test_no_match():
    assert exception_in_chain(ValueError(), FakeException) is False


def test_explicit_chained():
    e = ValueError()
    e.__cause__ = FakeException()

    assert exception_in_chain(e, FakeException)


def test_implicit_chained():
    e = ValueError()
    e.__context__ = FakeException()

    assert exception_in_chain(e, FakeException)


def test_deeply_chained_explicit():
    e = ValueError()
    e.__cause__ = FakeException()
    e.__cause__.__context__ = ChainedException()
    e.__cause__.__context__.__cause__ = DeepChainedException()

    assert exception_in_chain(e, DeepChainedException)


def test_deeply_chained_implicit():
    e = ValueError()
    e.__context__ = FakeException()
    e.__context__.__cause__ = ChainedException()
    e.__context__.__cause__.__context__ = DeepChainedException()

    assert exception_in_chain(e, DeepChainedException)


def test_fixed_len_list_slice_uses_bounded_redis_range():
    values = FixedLenList.__new__(FixedLenList)
    values.key = "values"
    values.red = mock.Mock()
    values.red.llen.return_value = 100_000
    values.red.lrange.return_value = [b"one", b"two", b"three"]
    values.deserializer = bytes.decode

    assert values[0:3] == ["one", "two", "three"]
    values.red.lrange.assert_called_once_with("values", 0, 2)


def test_fixed_len_list_empty_slice_does_not_read_redis_range():
    values = FixedLenList.__new__(FixedLenList)
    values.key = "values"
    values.red = mock.Mock()
    values.red.llen.return_value = 10
    values.deserializer = bytes.decode

    assert values[5:5] == []
    values.red.lrange.assert_not_called()


def test_fixed_len_list_add_batches_push_and_trim():
    values = FixedLenList.__new__(FixedLenList)
    values.key = "values"
    values.max_len = 3
    values.serializer = str.encode
    values.red = mock.Mock()
    pipe = values.red.pipeline.return_value

    values.add("four")

    pipe.lpush.assert_called_once_with("values", b"four")
    pipe.ltrim.assert_called_once_with("values", 0, 2)
    pipe.execute.assert_called_once_with()
