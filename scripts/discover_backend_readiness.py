"""Discover the running Compose configuration for readiness reconciliation.

Never guess missing files or combine configurations from different backends.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

if __package__:
    from .backend_health_override import BACKEND, HEALTHCHECK
else:
    from backend_health_override import BACKEND, HEALTHCHECK


def run(command: list[str]) -> str:
    return subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE).stdout


def main() -> int:
    root = Path.cwd().resolve(strict=True)
    base = ["docker", "compose", "-f", "compose.yaml"]
    names = sorted(name for name in run(base + ["config", "--services"]).split()
                   if BACKEND.fullmatch(name))
    if not names:
        raise ValueError("No configured backend services found")
    legacy = []
    running = []
    for name in names:
        ids = run(base + ["ps", "--all", "-q", name]).split()
        if not ids:
            continue
        if len(ids) != 1:
            raise ValueError(f"Expected at most one existing container for {name}")
        details = json.loads(run(["docker", "inspect", ids[0]]))[0]
        if not details["State"].get("Running"):
            continue
        running.append(name)
        if (details["Config"].get("Healthcheck") or {}).get("Test") != HEALTHCHECK["test"]:
            legacy.append((name, details["Config"].get("Labels") or {}))
    if not legacy:
        print("All running backends already have the readiness probe; stopped backends were left unchanged.")
        return 0

    configs = set()
    for name, labels in legacy:
        project = labels.get("com.docker.compose.project")
        working_dir = labels.get("com.docker.compose.project.working_dir")
        files = labels.get("com.docker.compose.project.config_files")
        if not project or not working_dir or not files:
            raise ValueError(f"{name} lacks Compose project labels; review required")
        if Path(working_dir).resolve(strict=True) != root:
            raise ValueError(f"{name} belongs to a different Compose directory")
        paths = tuple(files.split(","))
        if not all(path and Path(path).is_absolute() and Path(path).is_file() for path in paths):
            raise ValueError(f"{name} has missing or ambiguous Compose files; review required")
        configs.add((project, paths))
    if len(configs) != 1:
        raise ValueError("Backends use different Compose configurations; review required")
    project, files = configs.pop()
    command = [sys.executable, str(Path(__file__).resolve().with_name("reconcile_backend_readiness.py")),
               "--project-dir", str(root), "--project-name", project]
    for path in files:
        command += ["-f", path]
    for name in running:
        command += ["--service", name]
    command.append("--apply")
    # The reconciler validates configuration hashes, images, readiness and rollback.
    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Readiness discovery stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
