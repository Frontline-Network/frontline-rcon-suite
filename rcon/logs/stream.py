import datetime
import logging
import time
from collections import defaultdict

import redis

from rcon.cache_utils import get_redis_client
from rcon.rcon import Rcon, get_rcon
from rcon.types import StructuredLogLineWithMetaData
from rcon.user_config.log_stream import LogStreamUserConfig
from rcon.utils import Stream, StreamOlderElement, StreamID, StreamNoElements

logger = logging.getLogger(__name__)


class LogStream:
    # Each CRCON uses its own redis database, no need for keys to be unique across servers
    def __init__(
        self,
        rcon: Rcon | None = None,
        red: redis.StrictRedis | None = None,
        key="log_stream",
        maxlen: int | None = None,
    ) -> None:
        config = LogStreamUserConfig.load_from_db()
        self.rcon = rcon or get_rcon()
        self.red = red or get_redis_client()
        self.log_history_key = key
        self.log_stream = Stream(key=key, maxlen=maxlen or config.stream_size)

    def clear(self):
        logger.info("Clearing stream")
        self.red.delete(self.log_history_key)

    def bucket_by_timestamp(self, logs: list[StructuredLogLineWithMetaData]):
        """Organize logs by their game server timestamp

        Redis streams must be in sequential order, we use custom keys that are the
        unix timestamp of the time the log occurred on the game server, but each
        timestamp can have multiple logs.

        Return each unique timestamp and the logs that occured at that time
        """
        # logs has the newest logs first, oldest last
        buckets: dict[datetime.datetime, list[StructuredLogLineWithMetaData]] = (
            defaultdict(list)
        )

        ordered_logs: list[
            tuple[datetime.datetime, list[StructuredLogLineWithMetaData]]
        ] = []

        for log in reversed(logs):
            timestamp = datetime.datetime.fromtimestamp(log["timestamp_ms"] / 1000)
            buckets[timestamp].append(log)

        for timestamp in buckets.keys():
            ordered_logs.append((timestamp, buckets[timestamp]))

        return ordered_logs

    @staticmethod
    def _stream_id_parts(stream_id: str) -> tuple[int, int]:
        timestamp, sequence = stream_id.split("-", maxsplit=1)
        return int(timestamp), int(sequence)

    def _append_new_logs(
        self,
        logs: list[StructuredLogLineWithMetaData],
        last_seen_id: StreamID,
    ) -> tuple[StreamID, int]:
        """Append only entries newer than the current Redis stream tail."""
        last_seen_parts = (
            self._stream_id_parts(last_seen_id) if last_seen_id is not None else None
        )
        new_logs = 0

        for _timestamp, log_bucket in self.bucket_by_timestamp(logs):
            for idx, log in enumerate(log_bucket):
                timestamp_ms = log["timestamp_ms"] // 1000
                stream_id = f"{timestamp_ms}-{idx}"
                if (
                    last_seen_parts is not None
                    and self._stream_id_parts(stream_id) <= last_seen_parts
                ):
                    continue

                try:
                    last_seen_id = self.log_stream.add(custom_id=stream_id, obj=log)
                    last_seen_parts = self._stream_id_parts(last_seen_id)
                    new_logs += 1
                except StreamOlderElement:
                    # Another writer may have advanced the stream between the
                    # tail read and XADD. Preserve the previous safe behavior.
                    continue

        return last_seen_id, new_logs

    def run(
        self,
        loop_frequency_secs: int | None = None,
        initial_since_min: int | None = None,
        active_since_min: int | None = None,
    ):
        """Poll the game server and add new logs to the stream"""

        config = LogStreamUserConfig.load_from_db()

        since_min = initial_since_min or config.startup_since_mins
        logs = self.rcon.get_structured_logs(since_min_ago=since_min)["logs"]
        since_min = active_since_min or config.refresh_since_mins

        tail = self.log_stream.tail()
        last_seen_id = tail[0] if tail else None
        while True:
            config = LogStreamUserConfig.load_from_db()
            if not config.enabled:
                break
            last_seen_id, new_logs = self._append_new_logs(logs, last_seen_id)

            if new_logs:
                logger.info(f"Added {new_logs} new logs {last_seen_id=}")
            time.sleep(loop_frequency_secs or config.refresh_frequency_sec)
            logs = self.rcon.get_structured_logs(since_min_ago=since_min)["logs"]

    def logs_since(
        self, last_seen: StreamID | None = None, block_ms=500
    ) -> list[tuple[StreamID, StructuredLogLineWithMetaData]]:
        """Return a list of logs more recent than the last_seen ID"""
        try:
            if last_seen is None:
                logs: list[tuple[StreamID, StructuredLogLineWithMetaData]] = []
                tail_log: tuple[StreamID, StructuredLogLineWithMetaData] = (
                    self.log_stream.tail()
                )
                if tail_log:
                    logs.append(tail_log)
            else:
                logs: list[tuple[StreamID, StructuredLogLineWithMetaData]] = (
                    self.log_stream.read(last_id=last_seen, block_ms=block_ms)
                )
            return logs
        except StreamNoElements:
            response: list[tuple[StreamID, StructuredLogLineWithMetaData]] = []
            return response
