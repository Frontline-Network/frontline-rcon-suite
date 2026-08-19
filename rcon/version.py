from __future__ import annotations

import os
from collections.abc import Mapping
from subprocess import PIPE, run


def resolve_version(environment: Mapping[str, str] | None = None) -> str:
    """Resolve the deployed CRCON version without requiring Git in the image."""

    env = os.environ if environment is None else environment
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
