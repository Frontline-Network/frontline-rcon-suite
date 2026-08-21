import os
from logging import getLogger
from unittest import mock

import redis
import redis.exceptions
import pytest

from rcon import cache_utils
from rcon.cache_utils import REDIS_SCAN_COUNT, RedisCached, invalidates_for, ttl_cache

logger = getLogger(__name__)


class MockRedis:
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def get(self, key):
        raise redis.exceptions.RedisError

    def setex(self, _1, _2, _3):
        pass


class MockRedisDeleteUnavailable(MockRedis):
    def delete(self, _key):
        raise redis.exceptions.RedisError


def _needs_qual_name():
    pass


@pytest.mark.parametrize("ttl", [0, -1, 0.5, "60", None, False, True])
def test_redis_cached_rejects_invalid_ttl_before_cache_initialization(ttl):
    with pytest.raises(ValueError, match="positive whole number of seconds"):
        RedisCached(
            pool=None,
            red=mock.Mock(),
            ttl_seconds=ttl,
            function=_needs_qual_name,
        )


@pytest.mark.parametrize("ttl", [0, -1, 0.5, "60", None, False, True])
def test_ttl_cache_rejects_invalid_ttl_before_selecting_backend(ttl):
    with pytest.raises(ValueError, match="positive whole number of seconds"):
        ttl_cache(ttl)


def test_redis_cached_accepts_positive_integer_ttl():
    cached = RedisCached(
        pool=None,
        red=mock.Mock(),
        ttl_seconds=60,
        function=_needs_qual_name,
    )

    assert cached.ttl_seconds == 60


def test_cache_unavailable(monkeypatch):
    cached_func = mock.Mock(spec=_needs_qual_name)
    uncached_func = mock.Mock(spec=_needs_qual_name)

    c = RedisCached(
        pool=None,
        red=MockRedis(),
        ttl_seconds=1,
        function=cached_func,
        function_cache_unavailable=uncached_func,
        serializer=lambda x: None,
        deserializer=lambda x: None,
    )

    c()

    uncached_func.assert_called()
    cached_func.assert_not_called()


def test_cache_available():
    cached_func = mock.Mock(spec=_needs_qual_name)
    uncached_func = mock.Mock(spec=_needs_qual_name)

    c = RedisCached(
        pool=None,
        ttl_seconds=1,
        function=cached_func,
        function_cache_unavailable=uncached_func,
        serializer=lambda x: str(x),
        deserializer=lambda x: str(x),
    )

    c()

    # This test will only run successfully if there is an actual redis instance
    if os.getenv("HLL_REDIS_URL"):
        cached_func.assert_called()
        uncached_func.assert_not_called()


def test_stale_cache_miss_returns_immediately_and_refreshes_once_in_background():
    red = mock.Mock()
    cached = RedisCached(
        pool=None,
        red=red,
        ttl_seconds=60,
        function=_needs_qual_name,
        is_method=False,
    )

    def get_value(key):
        return '"stale"' if str(key).endswith("__stale") else None

    red.get.side_effect = get_value
    red.set.side_effect = [True, False]

    with (
        mock.patch.object(cached, "_refresh_stale_in_background") as refresh,
        mock.patch.object(cache_utils.time, "sleep", side_effect=AssertionError),
    ):
        assert cached() == "stale"
        assert cached() == "stale"

    refresh.assert_called_once()


def test_cold_lock_contention_does_not_sleep_before_fallback_execution():
    red = mock.Mock()
    red.get.return_value = None
    red.set.return_value = False
    function = mock.Mock(return_value="fresh")
    function.__name__ = "cold_refresh"
    function.__qualname__ = "cold_refresh"
    cached = RedisCached(
        pool=None,
        red=red,
        ttl_seconds=60,
        function=function,
        is_method=False,
    )

    with mock.patch.object(cache_utils.time, "sleep", side_effect=AssertionError):
        assert cached() == "fresh"

    function.assert_called_once_with()


def test_mem_cache_used(monkeypatch):
    monkeypatch.setenv("DEBUG", "True")
    # This is kind of janky but cachetools returns a decorated function not a class instance
    # so we can't isinstance check it
    c = ttl_cache(ttl=1)
    assert not isinstance(c, RedisCached)


def test_clear_for_tolerates_unavailable_redis():
    cached_func = mock.Mock(spec=_needs_qual_name)
    cached = RedisCached(
        pool=None,
        red=MockRedisDeleteUnavailable(),
        ttl_seconds=1,
        function=cached_func,
    )

    cached.clear_for()


def test_memory_cache_exposes_compatible_clear_for(monkeypatch):
    monkeypatch.setenv("DEBUG", "1")
    monkeypatch.setattr(cache_utils, "get_redis_pool", lambda **kwargs: None)

    @cache_utils.ttl_cache(60, is_method=False)
    def cached_value():
        return object()

    first = cached_value()
    assert cached_value() is first
    cached_value.clear_for()
    assert cached_value() is not first


def test_clear_all_scans_cache_keys_in_larger_batches():
    red = mock.Mock()
    keys = [f"cached_value:{index}" for index in range(REDIS_SCAN_COUNT * 2 + 1)]
    red.scan_iter.return_value = iter(keys)
    red.delete.side_effect = [REDIS_SCAN_COUNT, REDIS_SCAN_COUNT, 1]
    cached_func = mock.Mock(spec=_needs_qual_name)
    cached = RedisCached(
        pool=None,
        red=red,
        ttl_seconds=1,
        function=cached_func,
    )

    with mock.patch.object(cache_utils.logger, "info") as log:
        deleted = cached.clear_all()

    red.scan_iter.assert_called_once_with(
        match=f"{cached.key_prefix}*", count=REDIS_SCAN_COUNT
    )
    assert deleted == len(keys)
    assert [len(call.args) for call in red.delete.call_args_list] == [
        REDIS_SCAN_COUNT,
        REDIS_SCAN_COUNT,
        1,
    ]
    assert all("cached_value:" not in str(call) for call in log.call_args_list)
    log.assert_called_once()
    assert "scanned=%d deleted=%d batches=%d duration_ms=%d" in log.call_args.args[0]


def test_clear_all_returns_completed_batches_when_scan_is_interrupted():
    def interrupted_scan():
        yield from (f"cached_value:{index}" for index in range(REDIS_SCAN_COUNT))
        raise redis.exceptions.RedisError("connection dropped")

    red = mock.Mock()
    red.scan_iter.return_value = interrupted_scan()
    red.delete.return_value = REDIS_SCAN_COUNT
    cached = RedisCached(
        pool=None,
        red=red,
        ttl_seconds=1,
        function=mock.Mock(spec=_needs_qual_name),
    )

    with mock.patch.object(cache_utils.logger, "exception") as interrupted:
        deleted = cached.clear_all()

    assert deleted == REDIS_SCAN_COUNT
    red.delete.assert_called_once()
    assert len(red.delete.call_args.args) == REDIS_SCAN_COUNT
    assert "scanned=%d deleted=%d batches=%d" in interrupted.call_args.args[0]


def test_invalidates_for_clears_exact_key_before_and_after():
    cached_func = mock.Mock()

    with invalidates_for(cached_func):
        cached_func.clear_for.assert_called_once_with()
        cached_func.cache_clear.assert_not_called()

    assert cached_func.clear_for.call_count == 2
    cached_func.cache_clear.assert_not_called()
