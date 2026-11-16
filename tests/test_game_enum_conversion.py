import pytest

from rcon.types import GameEnum, GameIntEnum


@pytest.mark.parametrize('game', list(GameEnum))
def test_game_identifiers_round_trip(game):
    assert GameEnum.from_int(game.to_int()) is game
    assert GameEnum.from_int(int(game.to_int())) is game


def test_unknown_game_identifier_is_rejected():
    with pytest.raises(ValueError):
        GameEnum.from_int(max(GameIntEnum) + 1)
