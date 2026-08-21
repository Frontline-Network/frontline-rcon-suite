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
        clock=None,
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
        self._clock = clock or time.time

    @staticmethod
    def _as_text(value) -> str:
        return value.decode() if isinstance(value, bytes) else str(value)

    def _source_rules(self) -> list[tuple[str, int, str]]:
        """Normalize TS.INFO compaction rules across Redis client versions."""
        info = self.client.ts().info(self.NAME)
        rules = info.get("rules", []) if isinstance(info, dict) else info.rules
        normalized = []
        for rule in rules or []:
            if isinstance(rule, dict):
                destination = rule.get("destKey", rule.get("key"))
                duration = rule.get("bucketDuration", rule.get("timeBucket"))
                aggregation = rule.get("aggregationType", rule.get("aggregator"))
            else:
                destination, duration, aggregation, *_ = rule
            normalized.append(
                (
                    self._as_text(destination),
                    int(duration),
                    self._as_text(aggregation).lower(),
                )
            )
        return normalized

    @staticmethod
    def _versioned_rule_name(rule_name: str, aggregation: str, duration: int) -> str:
        """Build a deterministic destination name for a changed aggregation."""
        return f"{rule_name}__v_{aggregation.lower()}_{duration}"

    def _create_aggregation_rule(
        self, rule_name: str, aggregation: str, duration: int
    ) -> None:
        try:
            self.client.ts().create(rule_name)
        except redis.exceptions.ResponseError:
            logger.debug("Aggregation destination already exists: %s", rule_name)
        self.client.ts().createrule(self.NAME, rule_name, aggregation, duration)

    def migrate(self):
        self.ts = self.client.ts()
        try:
            logger.debug(
                "Creating timeseries %s with ms retention %s",
                self.NAME,
                self.retention_msecs,
            )
            self.ts.create(self.NAME, retention_msecs=self.retention_msecs)
        except redis.exceptions.ResponseError:
            logger.debug(
                "Already exists. Updating timeseries %s with ms retention %s",
                self.NAME,
                self.retention_msecs,
            )
            self.ts.alter(self.NAME, retention_msecs=self.retention_msecs)

        existing_rules = self._source_rules()
        for slice_name, (rule_name, agg_method, time_resolution) in list(
            self.slices.items()
        ):
            expected = (rule_name, time_resolution, agg_method.lower())
            if expected in existing_rules:
                continue

            configured_rule = next(
                (rule for rule in existing_rules if rule[0] == rule_name), None
            )
            if configured_rule is not None:
                versioned_name = self._versioned_rule_name(
                    rule_name, agg_method, time_resolution
                )
                versioned_expected = (versioned_name, time_resolution, agg_method.lower())
                self.slices[slice_name] = (
                    versioned_name,
                    agg_method,
                    time_resolution,
                )
                if versioned_expected in existing_rules:
                    logger.info(
                        "Using existing migrated aggregation %s for legacy rule %s",
                        versioned_name,
                        rule_name,
                    )
                    continue
                logger.warning(
                    "Aggregation rule %s is %s/%sms, expected %s/%sms; "
                    "creating versioned rule %s and retaining historical data",
                    rule_name,
                    configured_rule[2],
                    configured_rule[1],
                    agg_method,
                    time_resolution,
                    versioned_name,
                )
                self._create_aggregation_rule(
                    versioned_name, agg_method, time_resolution
                )
                existing_rules.append(versioned_expected)
                continue

            logger.debug("Creating timeseries aggregation %s", rule_name)
            self._create_aggregation_rule(rule_name, agg_method, time_resolution)
            existing_rules.append(expected)

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
        now = self._clock()
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
