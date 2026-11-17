"""Safely reconcile readiness checks on an already deployed Compose revision.

Use the exact Compose files and project name that produced the running
containers. By default this is a read-only preflight; --apply recreates only
outdated backend services after verifying their configuration and images.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__:
    from .backend_health_override import BACKEND, HEALTHCHECK, build_override
else:
    from backend_health_override import BACKEND, HEALTHCHECK, build_override

PROBE = ('import sys; from pathlib import Path; '
         'p=Path("/code/scripts/backend_healthcheck.py"); '
         'u=Path("/code/rconweb/rconweb/urls.py"); '
         'sys.exit(0 if p.is_file() and u.is_file() and "healthz" in u.read_text() else 1)')


def run(command: list[str], *, capture: bool = True) -> str:
    result = subprocess.run(command, check=True, text=True,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout if capture else ""


def service_hash(compose: list[str], name: str) -> str:
    lines = run(compose + ["config", "--hash", name]).strip().splitlines()
    if len(lines) != 1:
        raise ValueError(f"Could not resolve Compose hash for {name}")
    parts = lines[0].split()
    if len(parts) != 2 or parts[0] != name or len(parts[1]) != 64:
        raise ValueError(f"Unexpected Compose hash output for {name}")
    return parts[1]


def without_health(config: dict, names: list[str]) -> dict:
    result = json.loads(json.dumps(config))
    for name in names:
        result["services"][name].pop("healthcheck", None)
    return result


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--project-name")
    parser.add_argument("-f", "--file", action="append", required=True,
                        help="Active Compose file; repeat in the original order")
    parser.add_argument("--profile", action="append", default=[])
    parser.add_argument("--service", action="append", default=[],
                        help="Limit reconciliation to the named existing backends")
    parser.add_argument("--wait-timeout", type=int, default=300,
                        help="Readiness timeout in seconds (1–600, default: 300)")
    parser.add_argument("--apply", action="store_true", help="Recreate validated backends")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    if not 1 <= args.wait_timeout <= 600:
        raise ValueError("Wait timeout must be between 1 and 600 seconds")
    project_dir = args.project_dir.resolve(strict=True)
    compose = ["docker", "compose", "--project-directory", str(project_dir)]
    if args.project_name:
        compose += ["--project-name", args.project_name]
    for profile in args.profile:
        compose += ["--profile", profile]
    base_compose = compose.copy()
    for index, path in enumerate(args.file):
        candidate = Path(path)
        resolved_file = str((project_dir / candidate).resolve(strict=True))
        compose += ["-f", resolved_file]
        if index == 0:
            base_compose += ["-f", resolved_file]

    original = json.loads(run(compose + ["config", "--format", "json"]))
    services = original.get("services", {})
    # Shared overrides can mention backend_2..4 even on one-server hosts.
    # Only the installation's first Compose file defines actual services.
    base_services = set(run(base_compose + ["config", "--services"]).split())
    names = sorted(name for name in services if name in base_services and BACKEND.fullmatch(name))
    if args.service:
        if not set(args.service).issubset(names):
            raise ValueError("Requested backend is absent from the supplied Compose configuration")
        names = [name for name in names if name in args.service]
    if not names:
        raise ValueError("No configured backend services found")

    with tempfile.TemporaryDirectory(prefix="frontline-readiness-") as temporary:
        override = Path(temporary) / "readiness.json"
        contents = json.dumps(build_override(names), sort_keys=True)
        override.write_text(contents, encoding="utf-8")
        target = compose + ["-f", str(override)]
        resolved = json.loads(run(target + ["config", "--format", "json"]))
        if without_health(original, names) != without_health(resolved, names):
            raise ValueError("Readiness override changes other Compose settings")

        outdated: list[str] = []
        old_probes: dict[str, object] = {}
        checked_images: set[str] = set()
        expected_images: dict[str, str] = {}
        for name in names:
            ids = run(compose + ["ps", "--all", "-q", name]).split()
            if len(ids) != 1:
                raise ValueError(f"Expected exactly one existing container for {name}")
            details = json.loads(run(["docker", "inspect", ids[0]]))[0]
            if not details["State"].get("Running"):
                raise ValueError(f"{name} is not running; refusing to start it")
            current = details["Config"].get("Healthcheck") or {}
            if current.get("Test") == HEALTHCHECK["test"]:
                print(f"{name}: readiness probe already configured")
                continue
            labels = details["Config"].get("Labels") or {}
            if labels.get("com.docker.compose.config-hash") != service_hash(compose, name):
                raise ValueError(f"{name} differs from supplied Compose files; review required")
            image = services[name].get("image")
            if not isinstance(image, str) or not image:
                raise ValueError(f"{name} has no explicit image")
            image_id = run(["docker", "image", "inspect", "--format", "{{.Id}}", image]).strip()
            if image_id != details["Image"]:
                raise ValueError(f"{name} image differs from the supplied Compose configuration")
            expected_images[image] = image_id
            if image_id not in checked_images:
                run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "python",
                     image_id, "-c", PROBE])
                checked_images.add(image_id)
            outdated.append(name)
            old_probes[name] = current.get("Test")
            print(f"{name}: legacy readiness check can be reconciled")

        if not outdated:
            print("No backend readiness changes are needed.")
            return 0
        if not args.apply:
            print("Preflight only; run with --apply to recreate the listed backends.")
            return 0

        state_dir = project_dir / ".deploy-state"
        state_dir.mkdir(mode=0o700, exist_ok=True)
        persistent = state_dir / "backend-readiness-override.json"
        if persistent.exists() and persistent.read_text(encoding="utf-8") != contents:
            raise ValueError("Existing readiness override differs; review it before applying")
        if not persistent.exists():
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=state_dir,
                                             prefix=".backend-readiness-", delete=False) as handle:
                handle.write(contents)
                tmp_name = handle.name
            os.chmod(tmp_name, 0o600)
            os.replace(tmp_name, persistent)
        target = compose + ["-f", str(persistent)]
        def images_unchanged() -> bool:
            return all(run(["docker", "image", "inspect", "--format", "{{.Id}}", image]).strip() == image_id
                       for image, image_id in expected_images.items())

        if (json.loads(run(compose + ["config", "--format", "json"])) != original
                or json.loads(run(target + ["config", "--format", "json"])) != resolved
                or not images_unchanged()):
            raise ValueError("Compose configuration or image changed during preflight")
        for name in outdated:
            ids = run(compose + ["ps", "--all", "-q", name]).split()
            if len(ids) != 1:
                raise ValueError(f"{name} container changed during preflight")
            details = json.loads(run(["docker", "inspect", ids[0]]))[0]
            if (not details["State"].get("Running")
                    or details["Image"] != expected_images[services[name]["image"]]
                    or (details["Config"].get("Labels") or {}).get("com.docker.compose.config-hash") != service_hash(compose, name)):
                raise ValueError(f"{name} container changed during preflight")
        try:
            run(target + ["up", "-d", "--no-deps", "--no-build", "--pull", "never",
                          "--wait", "--wait-timeout", str(args.wait_timeout), *outdated], capture=False)
            # Some Compose versions can exit successfully on --wait-timeout
            # while health is still starting. Inspect the actual containers.
            for name in outdated:
                ids = run(target + ["ps", "--all", "-q", name]).split()
                if len(ids) != 1:
                    raise ValueError(f"Expected exactly one reconciled container for {name}")
                details = json.loads(run(["docker", "inspect", ids[0]]))[0]
                if (not details["State"].get("Running")
                        or details["State"].get("Health", {}).get("Status") != "healthy"
                        or (details["Config"].get("Healthcheck") or {}).get("Test") != HEALTHCHECK["test"]
                        or details["Image"] != expected_images[services[name]["image"]]):
                    raise ValueError(f"{name} did not become healthy with the expected probe and image")
        except (subprocess.CalledProcessError, ValueError):
            # Do not apply an old configuration if an operator changed the
            # input files while the reconciliation was running.
            if json.loads(run(compose + ["config", "--format", "json"])) == original and images_unchanged():
                print("Reconciliation failed; restoring the previous Compose configuration.", file=sys.stderr)
                run(compose + ["up", "-d", "--no-deps", "--no-build", "--pull", "never",
                               *outdated], capture=False)
                for name in outdated:
                    ids = run(compose + ["ps", "--all", "-q", name]).split()
                    if len(ids) != 1:
                        raise ValueError(f"Could not verify restored container for {name}")
                    details = json.loads(run(["docker", "inspect", ids[0]]))[0]
                    if (not details["State"].get("Running")
                            or (details["Config"].get("Healthcheck") or {}).get("Test") != old_probes[name]
                            or details["Image"] != expected_images[services[name]["image"]]):
                        raise ValueError(f"Could not verify restored configuration for {name}")
                print("Previous running backend configuration restored.", file=sys.stderr)
            else:
                print("Compose configuration changed; automatic rollback was not attempted.", file=sys.stderr)
            raise
        print(f"Reconciled {len(outdated)} backend(s). Keep {persistent} in subsequent Compose commands.")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"Readiness reconciliation stopped: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)
