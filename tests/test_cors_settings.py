import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_explicit_cors_origins_are_normalized_and_deduplicated():
    environment = os.environ.copy()
    environment.update(
        {
            "CORS_ALLOWED_ORIGINS": (
                " https://webapp.fln.gg/,https://ops.fln.gg,"
                "https://webapp.fln.gg "
            ),
            "HLL_MAINTENANCE_CONTAINER": "true",
        }
    )
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(ROOT), environment.get("PYTHONPATH")))
    )
    command = (
        "import json; "
        "from rconweb import settings; "
        "print('CORS_JSON=' + json.dumps(settings.CORS_ALLOWED_ORIGINS))"
    )

    result = subprocess.run(
        [sys.executable, "-c", command],
        cwd=ROOT / "rconweb",
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    origins = json.loads(
        next(
            line.removeprefix("CORS_JSON=")
            for line in result.stdout.splitlines()
            if line.startswith("CORS_JSON=")
        )
    )

    assert origins.count("https://webapp.fln.gg") == 1
    assert "https://ops.fln.gg" in origins
