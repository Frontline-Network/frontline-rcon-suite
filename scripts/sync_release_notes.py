"""Copy private GitHub release text into the backend before building its image.

CI supplies CRCON_RELEASES_GITHUB_TOKEN from its short-lived GITHUB_TOKEN.
Only note text and release metadata enter the image; no token or GitHub URLs.
"""
import json
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

# CI has only the Python standard library before the Docker build. Importing
# the rcon package would initialize the application and require its services.
spec = importlib.util.spec_from_file_location("release_channel", Path(__file__).resolve().parents[1] / "rcon/release_channel.py")
channel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(channel)


def main():
    token = channel.release_token()
    if not token:
        raise SystemExit("Release-note build credential is missing.")
    releases = []
    try:
        for page in range(1, 4):
            batch = channel.github_json(f"?per_page=100&page={page}", token)
            if not isinstance(batch, list):
                raise ValueError("Invalid release list")
            for item in batch:
                if item.get("draft") is False:
                    releases.append({key: item.get(key) for key in (
                        "tag_name", "name", "body", "published_at", "prerelease", "draft")})
            if len(batch) < 100:
                break
    except Exception:
        # Avoid exception/request dumps containing the build credential.
        raise SystemExit("Could not synchronize release notes; build stopped.") from None
    channel.SNAPSHOT_PATH.write_text(json.dumps({
        "checked_at": datetime.now(timezone.utc).isoformat(), "releases": releases,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Bundled {len(releases)} published release notes for the backend.")


if __name__ == "__main__":
    main()
