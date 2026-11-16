"""Exercise the real Redis/RQ scheduler against an isolated test Redis only."""
import os
import subprocess
import sys
import time
import uuid
from unittest.mock import patch

from rq import Queue
from rcon.cache_utils import get_redis_client
from rcon.end_match_stats import schedule_squad_message

assert os.environ.get("HLL_REDIS_HOST") == "afl-ui-test-redis"
red = get_redis_client()
suffix = uuid.uuid4().hex
queue_name = f"afl-stats-test-{suffix}"
result_key = f"afl-stats-test-result:{suffix}"
worker_script = r'''
import os
from contextlib import nullcontext
from rq import Queue, SimpleWorker
from rcon.cache_utils import get_redis_client
from rcon.user_config.end_match_stats import EndMatchStatsUserConfig
import rcon.rcon
import rcon.end_match_stats
class FakeRcon:
    def without_retries(self):
        return nullcontext()
    def message_all_players(self, message):
        get_redis_client().set(os.environ["TEST_RESULT_KEY"], message, ex=60)
        return True
rcon.rcon.get_rcon = lambda: FakeRcon()
rcon.end_match_stats.MapsHistory = lambda: [{"start": 100, "guessed": False}]
EndMatchStatsUserConfig.load_from_db = classmethod(lambda cls, **kwargs: cls(enabled=True, include_squads=True))
red = get_redis_client()
SimpleWorker([Queue(os.environ["TEST_QUEUE"], connection=red)], connection=red).work(with_scheduler=True, logging_level="WARNING")
'''
env = {**os.environ, "TEST_QUEUE": queue_name, "TEST_RESULT_KEY": result_key}
worker = None
try:
    queue = Queue(queue_name, connection=red)
    with patch("rcon.workers.get_queue", return_value=queue):
        schedule_squad_message("test squad ranking", time.time(), 5, 100)
    started = time.monotonic()
    worker = subprocess.Popen([sys.executable, "-c", worker_script], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    while time.monotonic() - started < 35:
        if red.get(result_key):
            elapsed = time.monotonic() - started
            assert elapsed >= 4, f"delivered too early: {elapsed:.1f}s"
            assert red.get(result_key) == b"test squad ranking"
            print(f"PASS real RQ scheduled delivery after {elapsed:.1f}s")
            break
        if worker.poll() is not None:
            raise RuntimeError(f"Test worker stopped: {worker.returncode}")
        time.sleep(0.5)
    else:
        raise RuntimeError("Scheduled message not delivered within 35 seconds")
finally:
    if worker:
        worker.terminate()
        try:
            worker.wait(timeout=10)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait(timeout=5)
    red.delete(result_key)
