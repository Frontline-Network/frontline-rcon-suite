"""Check the shipped backend runtime, including assets used by release checks.

Run inside the actual image with --network none and --entrypoint python.
Does not start workers, connect to a database, or perform game-server actions.
"""

import argparse
import importlib
import importlib.metadata
import json
import os
import shutil
from pathlib import Path


def check(version=None, slim=False):
    root = Path("/code")
    required = (
        "entrypoint.sh",
        "manage.py",
        "alembic.ini",
        "alembic/env.py",
        "rcon/cli.py",
        "rcon/cache_migrations/__main__.py",
        "rcon/release_notes.json",
        "rconweb/manage.py",
        "rconweb/rconweb/asgi.py",
        "rconweb/rconweb/wsgi.py",
        "scripts/backend_healthcheck.py",
        "scripts/release_smoke_server.py",
        "scripts/verify_bundled_release.py",
        "docs/releases/v0.9.3.md",
        "requirements.lock",
        "requirements-vcs.txt",
        "LICENSE",
    )
    for name in required:
        assert (root / name).is_file(), f"Missing runtime/release file: {name}"
    for name in ("entrypoint.sh", "manage.py", "rconweb/manage.py"):
        assert os.access(root / name, os.X_OK), f"Not executable: {name}"
    for name, pattern in (
        ("alembic/versions", "*.py"),
        ("rconweb/api/migrations", "*.py"),
        ("rconweb/templates", "**/*.html"),
        ("rconweb/static", "**/*.js"),
    ):
        assert any((root / name).glob(pattern)), f"Missing runtime assets: {name}"
    commands = (
        "bash",
        "cron",
        "logrotate",
        "ps",
        "supervisord",
        "supervisorctl",
        "gunicorn",
        "daphne",
        "alembic",
    )
    for command in commands:
        assert shutil.which(command), f"Missing runtime command: {command}"
    for module in ("psycopg2", "orjson", "cryptography.hazmat.bindings._rust"):
        importlib.import_module(module)
    actual_version = (root / "release_version").read_text().strip()
    if version is not None:
        assert actual_version == version, (actual_version, version)
    if slim:
        assert shutil.which("git") is None, "Build-only Git leaked into runtime"
        for name in (
            "rcongui",
            "rcongui_public",
            "assets",
            "tests",
            "discord_service",
            ".git",
            ".env",
            "Dockerfile",
        ):
            assert not (root / name).exists(), f"Unexpected backend content: {name}"
        assert not list(
            Path("/var/lib/apt/lists").glob("*_Packages*")
        ), "APT package indexes retained"
    return {
        "version": actual_version,
        "slim": slim,
        "required_files": len(required),
        "commands": list(commands),
        "packages": {
            dist.metadata["Name"].lower(): dist.version
            for dist in importlib.metadata.distributions()
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version")
    parser.add_argument("--slim", action="store_true")
    args = parser.parse_args()
    print(json.dumps(check(args.version, args.slim), sort_keys=True))
