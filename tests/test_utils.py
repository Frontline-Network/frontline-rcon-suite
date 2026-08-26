from unittest import mock

from rcon.game.hllv.maps import HLLV_LAYERS
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
