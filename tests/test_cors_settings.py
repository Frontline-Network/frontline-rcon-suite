import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_settings(environment_updates: dict[str, str | None]):
    environment = os.environ.copy()
    for key, value in environment_updates.items():
        if value is None:
            environment.pop(key, None)
        else:
            environment[key] = value
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(ROOT), environment.get("PYTHONPATH")))
    )
    return subprocess.run(
        [
            sys.executable,
            "-c",
            "from rconweb import settings; print('SETTINGS_LOADED')",
        ],
        cwd=ROOT / "rconweb",
        env=environment,
        capture_output=True,
        text=True,
    )


def test_explicit_cors_origins_are_normalized_and_deduplicated():
    environment = os.environ.copy()
    environment.update(
        {
            "CORS_ALLOWED_ORIGINS": (
                " https://webapp.fln.gg/,https://ops.fln.gg,"
                "https://webapp.fln.gg "
            ),
            "HLL_MAINTENANCE_CONTAINER": "true",
            "RCONWEB_TEST_MODE": "true",
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


def test_debug_flag_uses_explicit_boolean_values_only():
    result = _load_settings(
        {
            "HLL_MAINTENANCE_CONTAINER": "true",
            "RCONWEB_TEST_MODE": "true",
            "DJANGO_DEBUG": "false",
        }
    )
    assert result.returncode == 0, result.stderr

    invalid = _load_settings(
        {
            "HLL_MAINTENANCE_CONTAINER": "true",
            "RCONWEB_TEST_MODE": "true",
            "DJANGO_DEBUG": "definitely",
        }
    )
    assert invalid.returncode != 0
    assert "DJANGO_DEBUG must be one of" in invalid.stderr


def test_browser_session_cookie_is_not_readable_by_javascript():
    command = (
        "from rconweb import settings; "
        "assert settings.SESSION_COOKIE_HTTPONLY is True; "
        "print('SESSION_COOKIE_HTTPONLY=true')"
    )
    environment = os.environ.copy()
    environment.update(
        {
            "HLL_MAINTENANCE_CONTAINER": "true",
            "RCONWEB_TEST_MODE": "true",
        }
    )
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(ROOT), environment.get("PYTHONPATH")))
    )
    verification = subprocess.run(
        [sys.executable, "-c", command],
        cwd=ROOT / "rconweb",
        env=environment,
        capture_output=True,
        text=True,
    )
    assert verification.returncode == 0, verification.stderr


def test_production_settings_require_a_non_default_secret():
    missing = _load_settings(
        {
            "HLL_MAINTENANCE_CONTAINER": "true",
            "RCONWEB_TEST_MODE": "false",
            "RCONWEB_API_SECRET": None,
            "DJANGO_DEBUG": "false",
        }
    )
    assert missing.returncode != 0
    assert "RCONWEB_API_SECRET must be set" in missing.stderr

    too_short = _load_settings(
        {
            "HLL_MAINTENANCE_CONTAINER": "true",
            "RCONWEB_TEST_MODE": "false",
            "RCONWEB_API_SECRET": "too-short",
            "DJANGO_DEBUG": "false",
        }
    )
    assert too_short.returncode == 0
    assert "too-short" not in too_short.stderr


def test_credentialed_cors_rejects_http_outside_debug_mode():
    result = _load_settings(
        {
            "HLL_MAINTENANCE_CONTAINER": "true",
            "RCONWEB_TEST_MODE": "true",
            "DJANGO_DEBUG": "false",
            "CORS_ALLOWED_ORIGINS": "http://webapp.fln.gg",
        }
    )
    assert result.returncode != 0
    assert "may only contain HTTPS origins" in result.stderr
