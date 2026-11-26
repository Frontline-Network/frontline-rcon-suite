import atexit
import functools
import inspect
import logging
import os
import pickle
import threading
import time
import uuid
from contextlib import contextmanager, nullcontext
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
# A slow game-server read must not create one new thread every cache TTL.
# These are process limits, independent of freshness and stale-serving TTLs.
BACKGROUND_REFRESH_WORKERS = 4
CACHE_REFRESH_LEASE_SECONDS = 30
CACHE_REFRESH_RENEW_SECONDS = 5


class _BackgroundRefreshJob:
    def __init__(self, identity, function, renew, release, name, interval, lease_mutex):
        self.identity = identity
        self.function = function
        self.renew = renew
        self.release = release
        self.name = name
        self.next_renewal = time.monotonic() + interval
        self.lease_mutex = lease_mutex or threading.Lock()
        self.finishing = False
        self.lease_lost = False


class BackgroundRefreshCoordinator:
    """Bound active daemon refreshes without retaining an executor work queue.

    A single lazy keeper renews their distributed leases. Closing rejects new
    jobs but lets active jobs finish and release their own token; process exit
    never waits for daemon readers, and a crashed process leaves expiring leases.
    """

    def __init__(self, max_workers=BACKGROUND_REFRESH_WORKERS, renew_interval=CACHE_REFRESH_RENEW_SECONDS):
        self.max_workers = max_workers
        self.renew_interval = renew_interval
        self._reset()

    def _reset(self):
        self._mutex = threading.Lock()
        self._wake = threading.Event()
        self._active = {}
        self._keeper = None
        self._closed = False

    def after_fork(self):
        # Parent threads and their mutex owners do not survive fork. The child
        # must not retain their closures or release the parent's Redis leases.
        self._reset()

    def can_submit(self, identity):
        with self._mutex:
            return not self._closed and identity not in self._active and len(self._active) < self.max_workers

    def submit(self, identity, function, *, renew, release, name, lease_mutex=None):
        with self._mutex:
            if self._closed or identity in self._active or len(self._active) >= self.max_workers:
                return False
            job = _BackgroundRefreshJob(identity, function, renew, release, name, self.renew_interval, lease_mutex)
            self._active[identity] = job
            try:
                if self._keeper is None:
                    self._keeper = threading.Thread(target=self._keep_leases,
                        name="cache-refresh-leases", daemon=True)
                    self._keeper.start()
                worker = threading.Thread(target=self._execute, args=(job,), name=name, daemon=True)
                worker.start()
            except (RuntimeError, OSError, MemoryError):
                # No worker owns the lease until submit succeeds. The caller
                # releases it on rejection, including interpreter shutdown.
                self._active.pop(identity, None)
                if self._keeper is not None and not self._keeper.is_alive():
                    self._keeper = None
                self._wake.set()
                logger.exception("Unable to start bounded cache refresh")
                return False
            self._wake.set()
            return True

    def _execute(self, job):
        try:
            with self._mutex:
                run = not self._closed
            if run:
                job.function()
        except Exception:
            logger.exception("Unable to refresh stale cache value")
        finally:
            with self._mutex:
                job.finishing = True
            try:
                # Serialize renewal and release for this token, without holding
                # the process-wide mutex across any Redis I/O.
                with job.lease_mutex:
                    job.release()
            except Exception:
                logger.exception("Unable to release background refresh lease")
            finally:
                with self._mutex:
                    self._active.pop(job.identity, None)
                    self._wake.set()

    def _keep_leases(self):
        while True:
            with self._mutex:
                if not self._active:
                    if self._closed:
                        self._keeper = None
                        return
                jobs = tuple(self._active.values())
            if not jobs:
                # Keep the one daemon keeper asleep between refreshes instead
                # of creating another native thread on every short cache TTL.
                self._wake.wait()
                self._wake.clear()
                continue
            now = time.monotonic()
            for job in jobs:
                if job.finishing or job.lease_lost or job.next_renewal > now:
                    continue
                try:
                    with job.lease_mutex:
                        if not job.finishing:
                            if job.renew() is False:
                                job.lease_lost = True
                            job.next_renewal = time.monotonic() + self.renew_interval
                except Exception:
                    # An uncertain Redis result does not authorize deleting or
                    # replacing a lease. Publication rechecks its current token.
                    logger.exception("Unable to renew background refresh lease")
                    job.next_renewal = time.monotonic() + self.renew_interval
            # Do not keep a completed job's callback/arguments in this frame
            # while waiting for another lease-renewal interval.
            del jobs
            job = None
            self._wake.wait(self.renew_interval)
            self._wake.clear()

    def close(self):
        with self._mutex:
            self._closed = True
            self._wake.set()


_BACKGROUND_REFRESHES = BackgroundRefreshCoordinator()


def _shutdown_background_refreshes():
    _BACKGROUND_REFRESHES.close()


atexit.register(_shutdown_background_refreshes)
if hasattr(os, "register_at_fork"):
    os.register_at_fork(after_in_child=lambda: _BACKGROUND_REFRESHES.after_fork())


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
        cache_version: str | None = None,
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
        self.cache_version = cache_version

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
        prefix = f"{self.PREFIX}{self.function.__qualname__}"
        return f"{prefix}:{self.cache_version}" if self.cache_version else prefix

    @property
    def epoch_key(self):
        key = f"cache_epoch:function:{self.function.__qualname__}"
        return f"{key}:{self.cache_version}" if self.cache_version else key

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

    def _store_cached_value(self, key, value, epochs, lease=None) -> None:
        serialized = self.serializer(value)
        try:
            with self.red.pipeline() as pipe:
                pipe.watch(self.GLOBAL_EPOCH, self.epoch_key)
                if lease is not None:
                    lock_key, lock_token = lease
                    pipe.watch(lock_key)
                    if pipe.get(lock_key) not in (lock_token, lock_token.encode()):
                        pipe.unwatch()
                        return
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

    def _refresh_cached_value(self, func, key, lease=None, lease_mutex=None):
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
                # Lease renewal changes the watched lock's expiry. Coordinate
                # our own renewal with publication; never hold it during the
                # slow read, and keep epoch invalidation independently fenced.
                with lease_mutex or nullcontext():
                    self._store_cached_value(key, value, epochs, lease=lease)
        except redis.exceptions.RedisError:
            # The RCON call succeeded, so continue serving its result even if
            # Redis disappears between the read and the write.
            logger.exception("Unable to set cache")
        return value

    def _renew_lock(self, lock_key, lock_token):
        try:
            with self.red.pipeline() as pipe:
                pipe.watch(lock_key)
                if pipe.get(lock_key) not in (lock_token, lock_token.encode()):
                    pipe.unwatch()
                    return False
                pipe.multi()
                pipe.expire(lock_key, CACHE_REFRESH_LEASE_SECONDS)
                return pipe.execute() == [True]
        except redis.exceptions.WatchError:
            return False
        except redis.exceptions.RedisError:
            logger.exception("Unable to renew cache refresh lock")
            return None

    def _refresh_stale_in_background(self, func, key, lock_key, lock_token) -> None:
        """Serve stale promptly and refresh only within the process budget."""
        # One installation's key must not suppress another Redis database's
        # refresh. Normal wrappers share a pool; distinct pools remain protected
        # by the distributed lease even when they refer to the same database.
        lease_mutex = threading.Lock()
        accepted = _BACKGROUND_REFRESHES.submit(
            self._background_refresh_identity(key),
            lambda: self._refresh_cached_value(func, key, lease=(lock_key, lock_token), lease_mutex=lease_mutex),
            renew=lambda: self._renew_lock(lock_key, lock_token),
            release=lambda: self._release_lock(lock_key, lock_token),
            name=f"cache-refresh-{self.__name__}",
            lease_mutex=lease_mutex,
        )
        if not accepted:
            self._release_lock(lock_key, lock_token)

    def _background_refresh_identity(self, key):
        return (id(getattr(self.red, "connection_pool", self.red)), key)

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

        if stale_val is not None and not _BACKGROUND_REFRESHES.can_submit(self._background_refresh_identity(key)):
            # The local budget or this key is already busy. Avoid another
            # distributed lock round trip on the common overload path.
            return self.deserializer(stale_val)

        # logger.debug("Cache MISS for %s", self.key(*args, **kwargs))
        try:
            lock_acquired = bool(
                self.red.set(
                    lock_key,
                    lock_token,
                    nx=True,
                    ex=CACHE_REFRESH_LEASE_SECONDS,
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
        if not key:
            return
        try:
            self.red.set(self.epoch_key, uuid.uuid4().hex)
        except redis.exceptions.RedisError:
            logger.exception("Unable to invalidate in-flight cache refreshes")
        try:
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
    cache_version: str | None = None,
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
            cache_version=cache_version,
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
