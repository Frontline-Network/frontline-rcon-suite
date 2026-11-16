import functools
import inspect
import logging
import os
import pickle
import threading
import time
import uuid
from contextlib import contextmanager
from typing import Callable

import redis
import redis.exceptions
import simplejson
from cachetools.func import ttl_cache as cachetools_ttl_cache

logger = logging.getLogger(__name__)

_REDIS_POOL = None
# We use the redis database with db number 0 as a shared database amongst all the containers
_GLOBAL_REDIS_POOL = None
REDIS_SCAN_COUNT = 500
STALE_CACHE_MIN_GRACE_SECONDS = 5
STALE_CACHE_MAX_GRACE_SECONDS = 300


def validate_ttl_seconds(ttl_seconds: object, *, setting: str = "ttl_seconds") -> int:
    """Return a Redis/cachetools-safe TTL or raise a configuration error.

    Redis expiry and cachetools have subtly different behaviour for floats,
    booleans and zero.  Accepting those values defers a deployment/configuration
    error to an arbitrary cache write, so validate at every public cache entry
    point instead.
    """

    if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
        raise ValueError(
            f"{setting} must be a positive whole number of seconds; "
            f"received {ttl_seconds!r}"
        )
    if ttl_seconds <= 0:
        raise ValueError(
            f"{setting} must be a positive whole number of seconds; "
            f"received {ttl_seconds!r}"
        )
    return ttl_seconds


def _clear_matching_cache_keys(red, match: str) -> int:
    """Delete matching keys incrementally without materialising their values.

    A large cache can contain hundreds of thousands of serialized request keys.
    Keeping them in a Python list is both unnecessary and potentially exposes
    request metadata in logs.  ``SCAN`` stays incremental while each bounded
    batch is deleted immediately.
    """

    started_at = time.monotonic()
    scanned = deleted = batches = 0
    pending: list[str | bytes] = []

    def flush_pending() -> None:
        nonlocal deleted, batches
        if not pending:
            return
        deleted += int(red.delete(*pending) or 0)
        batches += 1
        pending.clear()

    try:
        for key in red.scan_iter(match=match, count=REDIS_SCAN_COUNT):
            pending.append(key)
            scanned += 1
            if len(pending) >= REDIS_SCAN_COUNT:
                flush_pending()
        flush_pending()
    except redis.exceptions.RedisError:
        logger.exception(
            "Cache purge interrupted: scanned=%d deleted=%d batches=%d",
            scanned,
            deleted,
            batches,
        )
    finally:
        logger.info(
            "Cache purge completed: scanned=%d deleted=%d batches=%d duration_ms=%d",
            scanned,
            deleted,
            batches,
            int((time.monotonic() - started_at) * 1000),
        )
    return deleted


class RedisCached:
    PREFIX = "cached_"
    GLOBAL_EPOCH = "cache_epoch:global"

    def __init__(
        self,
        pool,
        ttl_seconds,
        function,
        function_cache_unavailable: Callable | None = None,
        red: redis.StrictRedis | None = None,
        is_method=False,
        cache_falsy=True,
        serializer=simplejson.dumps,
        deserializer=simplejson.loads,
    ):
        ttl_seconds = validate_ttl_seconds(ttl_seconds)
        if pool is None:
            pool = get_redis_pool()

        if red is None:
            self.red = redis.Redis(connection_pool=pool)
        else:
            self.red = red
        self.function = function
        self.function_cache_unavailable = function_cache_unavailable
        self.serializer = serializer
        self.deserializer = deserializer
        self.ttl_seconds = ttl_seconds
        self.is_method = is_method
        self.cache_falsy = cache_falsy

    @staticmethod
    def clear_all_caches(pool) -> int:
        red = redis.Redis(connection_pool=pool)
        try:
            red.set(RedisCached.GLOBAL_EPOCH, uuid.uuid4().hex)
        except redis.exceptions.RedisError:
            logger.exception("Unable to invalidate in-flight cache refreshes")
        return _clear_matching_cache_keys(red, f"{RedisCached.PREFIX}*")

    @property
    def key_prefix(self):
        return f"{self.PREFIX}{self.function.__qualname__}"

    @property
    def epoch_key(self):
        return f"cache_epoch:function:{self.function.__qualname__}"

    def key(self, *args, **kwargs):
        if self.is_method:
            args = args[1:]
        params = self.serializer({"args": args, "kwargs": kwargs})
        if isinstance(params, bytes):
            return self.key_prefix.encode() + b"__" + params
        return f"{self.key_prefix}__{params}"

    def lock_key(self, key):
        if isinstance(key, bytes):
            return b"lock_" + key
        return f"lock_{key}"

    def stale_key(self, key):
        """Keep the stale value under the same clearable cache prefix."""

        if isinstance(key, bytes):
            return key + b"__stale"
        return f"{key}__stale"

    @property
    def stale_ttl_seconds(self) -> int:
        """Bound stale serving to a short grace period after fresh expiry."""

        grace = max(
            STALE_CACHE_MIN_GRACE_SECONDS,
            min(STALE_CACHE_MAX_GRACE_SECONDS, self.ttl_seconds),
        )
        return self.ttl_seconds + grace

    @property
    def __name__(self):
        return self.function.__name__

    @property
    def __wrapped__(self):
        return self.function

    def _release_lock(self, lock_key, lock_token):
        try:
            with self.red.pipeline() as pipe:
                pipe.watch(lock_key)
                current_token = pipe.get(lock_key)
                if current_token in (lock_token, lock_token.encode()):
                    pipe.multi()
                    pipe.delete(lock_key)
                    pipe.execute()
                else:
                    pipe.unwatch()
        except redis.exceptions.RedisError:
            logger.exception("Unable to release cache refresh lock")

    def _store_cached_value(self, key, value, epochs) -> None:
        serialized = self.serializer(value)
        try:
            with self.red.pipeline() as pipe:
                pipe.watch(self.GLOBAL_EPOCH, self.epoch_key)
                if (pipe.get(self.GLOBAL_EPOCH), pipe.get(self.epoch_key)) != epochs:
                    pipe.unwatch()
                    return
                pipe.multi()
                pipe.setex(key, self.ttl_seconds, serialized)
                pipe.setex(self.stale_key(key), self.stale_ttl_seconds, serialized)
                pipe.execute()
        except redis.exceptions.WatchError:
            # Invalidation won the race; never retry an old value.
            return

    def _refresh_cached_value(self, func, key):
        epochs = None
        try:
            # Random persistent tokens also change after a Redis restart or
            # eviction, so an old in-flight read cannot match a reset counter.
            self.red.set(self.GLOBAL_EPOCH, uuid.uuid4().hex, nx=True)
            self.red.set(self.epoch_key, uuid.uuid4().hex, nx=True)
            epochs = (self.red.get(self.GLOBAL_EPOCH), self.red.get(self.epoch_key))
            if None in epochs:
                epochs = None
        except redis.exceptions.RedisError:
            logger.exception("Unable to read cache invalidation epochs")
        value = func()
        if not value and not self.cache_falsy:
            logger.debug("Caching falsy result is disabled for %s", self.__name__)
            return value
        try:
            if epochs is not None:
                self._store_cached_value(key, value, epochs)
        except redis.exceptions.RedisError:
            # The RCON call succeeded, so continue serving its result even if
            # Redis disappears between the read and the write.
            logger.exception("Unable to set cache")
        return value

    def _refresh_stale_in_background(self, func, key, lock_key, lock_token) -> None:
        """Refresh a stale key without holding the request thread open."""

        def refresh() -> None:
            try:
                self._refresh_cached_value(func, key)
            except Exception:
                logger.exception("Unable to refresh stale cache value")
            finally:
                self._release_lock(lock_key, lock_token)

        worker = threading.Thread(
            target=refresh,
            name=f"cache-refresh-{self.__name__}",
            daemon=True,
        )
        try:
            worker.start()
        except RuntimeError:
            # Do not leave an NX lock behind when process shutdown prevents
            # starting the refresh thread. The stale value remains usable.
            logger.exception("Unable to start stale cache refresh")
            self._release_lock(lock_key, lock_token)

    def __call__(self, *args, **kwargs):
        val = stale_val = None
        key = self.key(*args, **kwargs)
        lock_key = self.lock_key(key)
        lock_token = str(uuid.uuid4())
        lock_acquired = False
        cache_available = True
        refresh_without_lock = False
        func = self.function
        try:
            val = self.red.get(key)
        except redis.exceptions.RedisError as e:
            cache_available = False
            logger.exception("Unable to use cache: %s", e)
            if self.function_cache_unavailable:
                func = self.function_cache_unavailable
                logger.error("Using fallback function due to cache failure: %s", func)

        if val is not None:
            # logger.debug("Cache HIT for %s", self.key(*args, **kwargs))
            return self.deserializer(val)

        if not cache_available:
            return func(*args, **kwargs)

        try:
            stale_val = self.red.get(self.stale_key(key))
        except redis.exceptions.RedisError:
            logger.exception("Unable to use stale cache value")

        # logger.debug("Cache MISS for %s", self.key(*args, **kwargs))
        try:
            lock_acquired = bool(
                self.red.set(
                    lock_key,
                    lock_token,
                    nx=True,
                    ex=max(1, min(30, self.ttl_seconds)),
                )
            )
        except redis.exceptions.RedisError:
            logger.exception("Unable to acquire cache refresh lock")
            refresh_without_lock = True

        if stale_val is not None:
            if lock_acquired:
                self._refresh_stale_in_background(
                    lambda: func(*args, **kwargs), key, lock_key, lock_token
                )
            return self.deserializer(stale_val)

        if not lock_acquired and not refresh_without_lock:
            # A cold cache has no safe stale result to return. Do not sleep in
            # a request worker: retain availability while the lock owner
            # refreshes. Warm cache misses use stale-while-revalidate above.
            logger.debug("Cold cache refresh already in progress for %s", self.__name__)

        try:
            val = self._refresh_cached_value(lambda: func(*args, **kwargs), key)
        finally:
            if lock_acquired:
                self._release_lock(lock_key, lock_token)

        return val

    def get_cached_value_for(self, *args, **kwargs):
        if self.is_method:
            key = self.key(None, *args, **kwargs)
        else:
            key = self.key(*args, **kwargs)
        return self.red.get(key)

    def clear_for(self, *args, **kwargs):
        if self.is_method:
            key = self.key(None, *args, **kwargs)
        else:
            key = self.key(*args, **kwargs)
        logger.debug("Invalidating cache for %s", key)
        try:
            if key:
                self.red.set(self.epoch_key, uuid.uuid4().hex)
                self.red.delete(key, self.stale_key(key))
        except redis.exceptions.RedisError:
            logger.exception("Unable to clear cache key %s", key)

    def clear_all(self) -> int:
        try:
            self.red.set(self.epoch_key, uuid.uuid4().hex)
        except redis.exceptions.RedisError:
            logger.exception("Unable to invalidate in-flight cache refreshes")
        return _clear_matching_cache_keys(self.red, f"{self.key_prefix}*")


def construct_redis_url(db_number: int = 0) -> str:
    """Allow overriding the database number when creating a redis instance"""
    host = os.getenv("HLL_REDIS_HOST")
    port = os.getenv("HLL_REDIS_PORT")

    if not host or not port:
        raise ValueError(f"HLL_REDIS_HOST and HLL_REDIS_PORT must be set")

    return f"redis://{host}:{port}/{db_number}"


def get_global_redis_pool(redis_url: str | None = None, decode_responses=True):
    global _GLOBAL_REDIS_POOL
    if redis_url is None:
        redis_url = construct_redis_url(db_number=0)
    if not redis_url:
        return None

    if _GLOBAL_REDIS_POOL is None:
        logger.info("Global Redis pool initializing")
        _GLOBAL_REDIS_POOL = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=1000,
            socket_connect_timeout=5,
            socket_timeout=5,
            decode_responses=decode_responses,
        )

    return _GLOBAL_REDIS_POOL


def get_redis_pool(redis_url: str | None = None, decode_responses=True):
    global _REDIS_POOL
    if redis_url is None:
        redis_url = os.getenv("HLL_REDIS_URL")
    if not redis_url:
        return None

    if _REDIS_POOL is None:
        logger.info("Redis pool initializing")
        _REDIS_POOL = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=1000,
            socket_connect_timeout=5,
            socket_timeout=5,
            decode_responses=decode_responses,
        )

    return _REDIS_POOL


def get_redis_client(
    redis_url: str | None = None, decode_responses=True, global_pool: bool = False
):
    if global_pool:
        pool = get_global_redis_pool(
            redis_url=redis_url, decode_responses=decode_responses
        )
    else:
        pool = get_redis_pool(redis_url=redis_url, decode_responses=decode_responses)
    return redis.Redis(connection_pool=pool)


def ttl_cache(
    ttl,
    *args,
    is_method=True,
    cache_falsy=True,
    function_cache_unavailable=None,
    **kwargs,
):
    ttl = validate_ttl_seconds(ttl, setting="ttl")
    pool = get_redis_pool(decode_responses=False)

    def memory_cache_decorator(func):
        cached = cachetools_ttl_cache(*args, ttl=ttl, **kwargs)(func)

        # Keep the Redis-backed decorator contract available during tests,
        # maintenance and Redis outages. cachetools cannot evict one computed
        # key, so the safe local fallback clears only this function's cache.
        cached.clear_for = lambda *call_args, **call_kwargs: cached.cache_clear()
        return cached

    # Allow use of in memory cache and not redis when running tests
    # but still use redis when running the development web server
    if os.getenv("DEBUG") and not pool:
        logger.warning(f"Unable to connect to Redis, using memory cache")
        return memory_cache_decorator
    # the maintenance container does not use the redis cache but this method is imported
    # and it will fail if it can't connect to redis otherwise
    elif os.getenv("HLL_MAINTENANCE_CONTAINER") and not pool:
        # skip logging but still use the in memory cache tools to allow importing
        return memory_cache_decorator
    if not pool:
        logger.error("Unable to connect to Redis")
        raise ConnectionError("Unable to connect to Redis")

    def decorator(func):
        cached_func = RedisCached(
            pool,
            ttl,
            function=func,
            function_cache_unavailable=function_cache_unavailable,
            is_method=is_method,
            cache_falsy=cache_falsy,
            serializer=pickle.dumps,
            deserializer=pickle.loads,
        )

        def wrapper(*args, **kwargs):
            # Re-wrapping to preserve function signature
            return cached_func(*args, **kwargs)

        functools.update_wrapper(wrapper, func)
        wrapper.cache_clear = cached_func.clear_all
        wrapper.get_cached_value_for = cached_func.get_cached_value_for
        wrapper.clear_for = cached_func.clear_for
        wrapper.cache = cached_func
        return wrapper

    return decorator


@contextmanager
def invalidates(*cached_funcs):
    def clear_cached_func(cached_func) -> None:
        cache = getattr(cached_func, "cache", None)
        function = getattr(cache, "function", None)
        is_method = bool(getattr(cache, "is_method", False))

        if function is not None:
            parameters = list(inspect.signature(function).parameters.values())
            if is_method and parameters:
                parameters = parameters[1:]
            if not parameters:
                cached_func.clear_for()
                return

        cached_func.cache_clear()

    for f in cached_funcs:
        clear_cached_func(f)
    try:
        yield None
    finally:
        for f in cached_funcs:
            clear_cached_func(f)


@contextmanager
def invalidates_for(*cached_funcs):
    """Invalidate the exact no-argument key for each cached function."""
    for f in cached_funcs:
        f.clear_for()
    try:
        yield None
    finally:
        for f in cached_funcs:
            f.clear_for()
