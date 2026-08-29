import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_retired_stats_responses_never_turn_into_rate_limit_exceptions():
    script = """
import os

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ["DJANGO_SETTINGS_MODULE"] = "rconweb.test_settings"

import django
django.setup()

from django.core.cache import cache
from django.test import RequestFactory
from api.legacy_stats import get_player_list, get_scoreboard

cache.clear()
factory = RequestFactory()
responses = []
for _ in range(12):
    responses.append(get_player_list(factory.get("/api/get_player_list")))
    responses.append(get_scoreboard(factory.get("/api/get_scoreboard")))
assert all(response.status_code == 410 for response in responses)
print(len(responses))
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(ROOT / "rconweb"), str(ROOT), env.get("PYTHONPATH", "")]
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("24")
