from __future__ import annotations

import os
from collections.abc import Mapping
from subprocess import PIPE, run
from pathlib import Path

IMAGE_VERSION_PATH = Path(__file__).resolve().parents[1] / "release_version"


def resolve_version(environment: Mapping[str, str] | None = None) -> str:
    """Resolve the deployed CRCON version without requiring Git in the image."""

    env = os.environ if environment is None else environment
    try:
        image_version = IMAGE_VERSION_PATH.read_text(encoding="utf-8").strip()
        if image_version and image_version not in {"unknown", "development"}:
            return image_version
    except OSError:
        pass
    configured = str(env.get("CRCON_VERSION", "")).strip()
    if configured:
        return configured

    try:
        result = run(
            ["git", "describe", "--tags"],
            stdout=PIPE,
            stderr=PIPE,
            check=False,
        )
    except OSError:
        return "unknown"

    discovered = result.stdout.decode(errors="replace").strip()
    return discovered or "unknown"
