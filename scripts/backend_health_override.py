"""Generate a readiness override only for backends in the base Compose file."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND = re.compile(r"backend_([1-9][0-9]*)\Z")
HEALTHCHECK = {
    "disable": False,
    "test": ["CMD", "python", "/code/scripts/backend_healthcheck.py"],
    "interval": "15s",
    "timeout": "30s",
    "start_period": "30s",
    "retries": 5,
}


def build_override(service_names: list[str]) -> dict:
    services = {}
    for name in service_names:
        match = BACKEND.fullmatch(name)
        if match:
            services[name] = {"healthcheck": HEALTHCHECK.copy()}
    return {"services": services}


def backend_images(compose: dict, service_names: list[str]) -> list[str]:
    images = []
    for name in build_override(service_names)["services"]:
        image = compose.get("services", {}).get(name, {}).get("image")
        if not isinstance(image, str) or not image:
            raise ValueError(f"Backend {name} must have an explicit image for readiness verification")
        if image not in images:
            images.append(image)
    return images


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: backend_health_override.py OUTPUT|--images [SERVICE ...]")
    if sys.argv[1] == "--images":
        for image in backend_images(json.load(sys.stdin), sys.argv[2:]):
            print(image)
        return
    Path(sys.argv[1]).write_text(json.dumps(build_override(sys.argv[2:])), encoding="utf-8")


if __name__ == "__main__":
    main()
