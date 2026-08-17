import os
from pathlib import Path
from subprocess import PIPE, run


_VERSION_FILES = (Path("/code/tag_version"), Path(__file__).resolve().parents[1] / "tag_version")


def get_version() -> str:
    """Return a stable release version without requiring a Git checkout."""

    configured = os.getenv("CRCON_VERSION", "").strip()
    if configured and configured.lower() != "unknown":
        return configured

    for version_file in _VERSION_FILES:
        try:
            version = version_file.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if version and version.lower() != "unknown":
            return version

    try:
        result = run(
            ["git", "describe", "--tags"],
            stdout=PIPE,
            stderr=PIPE,
            check=False,
        )
    except OSError:
        return "unknown"

    version = result.stdout.decode(errors="replace").strip()
    return version if result.returncode == 0 and version else "unknown"
