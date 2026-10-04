"""Validate the actual release snapshot using the production parser (stdlib only)."""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_channel", ROOT / "rcon/release_channel.py")
channel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(channel)


def verify(version, require_highlights=False, image=False):
    snapshot = json.loads(channel.SNAPSHOT_PATH.read_text(encoding="utf-8"))
    selected = channel.select_releases(snapshot["releases"], version)
    current = next((entry for entry in selected if entry["current"]), None)
    assert current and current["tag_name"] == version, "Published release missing from image snapshot"
    if require_highlights:
        assert current["highlights"], "Published release has no valid DE/EN highlights"
        assert current["highlights"]["image"] == "theme-collection"
        assert current["highlights"]["action"]["id"] == "appearance"
        source = next(entry for entry in snapshot["releases"] if entry["tag_name"] == version)
        assert len(channel.HIGHLIGHT_BLOCK.findall(source["body"])) == 1
        reviewed = (ROOT / "docs/releases" / f"{version}.md").read_text(encoding="utf-8")
        assert source["body"].replace("\r\n", "\n").strip() == reviewed.strip(), "Image notes differ from reviewed release notes"
    # An old installation cannot announce this release, even with the new snapshot.
    assert all(entry["tag_name"] != version for entry in channel.select_releases(snapshot["releases"], "v0.8.8"))
    if image:
        assert (ROOT / "release_version").read_text().strip() == version
    print(json.dumps({"version": version, "current": current["tag_name"],
                      "highlights": bool(current["highlights"]), "source": "bundled"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("--require-highlights", action="store_true")
    parser.add_argument("--image", action="store_true")
    args = parser.parse_args()
    verify(args.version, args.require_highlights, args.image)
