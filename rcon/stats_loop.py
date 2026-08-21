import time
from logging import getLogger

import redis
import redis.exceptions

from rcon.cache_utils import get_redis_client
from rcon.connection import HLLServerError
from rcon.rcon import Rcon, get_rcon

logger = getLogger(__name__)

LOOP_FREQUENCY_SEC = 0.5
MAX_RETRY_DELAY_SEC = 60
EXPECTED_SNAPSHOT_ERRORS = (HLLServerError, OSError, TimeoutError, redis.exceptions.RedisError)


class Series:
    # CHILDREN MUST DEFINE A CLASS ATTRIBUTE: NAME
    NAME: str

    def __init__(
        self,
        client=None,
        min_resolution_ms=30000,
        retention_days=60,
        max_fails=5,
        slices=None,
    ):
        self.client: redis.Redis = client or get_redis_client()
        self.slices = slices or {
            "minute": (f"{self.NAME}avgRuleMinute", "avg", 1000 * 60),
            "hour": (f"{self.NAME}avgRuleHour", "avg", 1000 * 60 * 60),
            "day": (f"{self.NAME}avgRuleDay", "avg", 1000 * 60 * 60 * 24),
        }
        self.retention_msecs = 1000 * 60 * 60 * 24 * retention_days
        self.min_resolution_ms = min_resolution_ms / 1000
        self.last_run_time = 0
        self.fails = 0
        self.max_fails = max_fails
        self.last_error: str | None = None
        self.last_error_at: float | None = None
        self.next_retry_at = 0.0

    def migrate(self):
        try:
            logger.debug(
                "Creating timeseries %s with ms retention %s",
                self.NAME,
                self.retention_msecs,
            )
            self.ts = self.client.ts().create(
                self.NAME, retention_msecs=self.retention_msecs
            )
        except redis.exceptions.ResponseError:
            logger.debug(
                "Already exists. Updating timeseries %s with ms retention %s",
                self.NAME,
                self.retention_msecs,
            )
            self.ts.alter(self.NAME, retention_msecs=self.retention_msecs)

        for rule_name, agg_method, time_resolution in self.slices.values():
            logger.debug("Creating timeseries aggregation %s", rule_name)
            try:
                self.client.ts().create(rule_name)
                self.client.ts().createrule(
                    self.NAME, rule_name, agg_method, time_resolution
                )
            except redis.exceptions.ResponseError:
                logger.debug("Already exists timeseries aggregation %s", rule_name)
                pass  # rule already exists
                # TODO: Handle change

    def get_last(self):
        return self.client.get(self.NAME)

    def get_series(self, by="minute", start=0, end=-1):
        return self.client.ts().range(self.slices[by][0], start, end)

    def get_range(self, *args, **kwargs):
        # Exposes the series raw range function
        # https://oss.redislabs.com/redistimeseries/commands/#filtering
        return self.client.ts().range(self.NAME, *args, **kwargs)

    def snapshot(self, rcon: Rcon):
        raise NotImplementedError

    def health(self) -> dict[str, float | int | str | None | bool]:
        """Return a lightweight health signal for monitoring and diagnostics."""
        return {
            "name": self.NAME,
            "degraded": self.fails > 0,
            "consecutive_failures": self.fails,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at,
            "next_retry_at": self.next_retry_at or None,
            "last_success_at": self.last_run_time or None,
        }

    def _record_snapshot_failure(
        self, error: Exception, now: float, *, expected: bool
    ) -> None:
        self.fails += 1
        self.last_error = f"{type(error).__name__}: {error}"
        self.last_error_at = now
        retry_delay = min(MAX_RETRY_DELAY_SEC, 2 ** min(self.fails - 1, 6))
        self.next_retry_at = now + retry_delay
        message = (
            "Timeseries snapshot %s failed (%s, consecutive=%s); retrying in %ss"
        )
        if expected:
            logger.warning(message, self.NAME, self.last_error, self.fails, retry_delay)
        else:
            logger.exception(message, self.NAME, self.last_error, self.fails, retry_delay)

    def run_on_time(self, rcon):
        now = time.time()
        if now - self.last_run_time <= self.min_resolution_ms:
            return
        if now < self.next_retry_at:
            return
        logger.debug("Taking snaphost for %s", self.NAME)
        try:
            self.snapshot(rcon)
        except EXPECTED_SNAPSHOT_ERRORS as error:
            self._record_snapshot_failure(error, now, expected=True)
            if self.fails > self.max_fails:
                raise
            return
        except Exception as error:
            self._record_snapshot_failure(error, now, expected=False)
            if self.fails > self.max_fails:
                raise
            return
        self.last_run_time = now
        self.fails = 0
        self.last_error = None
        self.last_error_at = None
        self.next_retry_at = 0.0
        return now


class PlayerCount(Series):
    NAME = "player_count"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def snapshot(self, rcon):
        slots = rcon.get_slots()
        current_players = slots["current_players"]

        self.client.ts().add(self.NAME, "*", float(current_players))


def run():
    rcon = get_rcon()
    red = get_redis_client()
    registered_series = [PlayerCount(red)]
    for series in registered_series:
        series.migrate()

    while True:
        for series in registered_series:
            series.run_on_time(rcon)
        time.sleep(LOOP_FREQUENCY_SEC)


if __name__ == "__main__":
    run()
