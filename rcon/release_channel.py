"""Private GitHub release notes, limited to the version actually running here.

No repository URL, author, asset, or credential is returned to clients. Release
tags must be exact (development/git-describe builds fail closed).
"""

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

REPOSITORY = "Frontline-Network/frontline-rcon-suite"
API_ROOT = f"https://api.github.com/repos/{REPOSITORY}/releases"
VERSION = re.compile(r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:alpha|beta|rc)\.(?:0|[1-9]\d*)))?\Z")
CACHE_KEY = "crcon:release-channel:v2:"
SNAPSHOT_PATH = Path(__file__).with_name("release_notes.json")
HIGHLIGHT_BLOCK = re.compile(r"<!--\s*crcon-highlights\s*\n(.*?)-->", re.DOTALL)


def normalize_highlights(value):
    """Accept reviewed DE/EN copy and known UI actions/assets, never remote markup."""
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        return None

    def translated(text, limit):
        if not isinstance(text, dict):
            raise ValueError("Both translations are required")
        result = {}
        for lang in ("de", "en"):
            entry = text.get(lang)
            if not isinstance(entry, str) or not entry.strip() or len(entry) > limit:
                raise ValueError("Invalid highlight text")
            result[lang] = entry.strip()
        return result

    try:
        result = {
            "schema_version": 1,
            "title": translated(value.get("title"), 100),
            "description": translated(value.get("description"), 320),
            "items": [],
        }
        image = value.get("image")
        if image not in (None, "theme-collection"):
            return None
        if image:
            result.update(image=image, image_alt=translated(value.get("image_alt"), 180))
        action = value.get("action")
        if action is not None:
            if not isinstance(action, dict) or action.get("id") not in ("appearance", "documentation", "overview"):
                return None
            result["action"] = {"id": action["id"], "label": translated(action.get("label"), 60)}
        items = value.get("items", [])
        if not isinstance(items, list) or len(items) > 2:
            return None
        for item in items:
            if not isinstance(item, dict) or item.get("icon") not in ("shortcuts", "book", "palette", "overview"):
                return None
            result["items"].append({
                "icon": item["icon"], "title": translated(item.get("title"), 100),
                "description": translated(item.get("description"), 240),
            })
        return result
    except (ValueError, TypeError):
        return None


def extract_highlights(body):
    blocks = HIGHLIGHT_BLOCK.findall(body)
    notes = HIGHLIGHT_BLOCK.sub("", body).strip()
    if len(blocks) != 1 or len(blocks[0]) > 16000:
        return notes, None
    try:
        return notes, normalize_highlights(json.loads(blocks[0]))
    except (ValueError, TypeError):
        return notes, None


def parse_version(value):
    match = VERSION.fullmatch(value.strip()) if isinstance(value, str) else None
    return (tuple(map(int, match.group(1, 2, 3))), match[4]) if match else None


class NoRedirect(HTTPRedirectHandler):
    # In particular, never forward the private-repository credential elsewhere.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def github_json(path, token):
    request = Request(API_ROOT + path, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "Frontline-CRCON-Release-Channel",
    })
    with build_opener(NoRedirect).open(request, timeout=5) as response:
        body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise ValueError("Release response exceeds limit")
        return json.loads(body)


def release_token():
    path = os.getenv("CRCON_RELEASES_GITHUB_TOKEN_FILE", "").strip()
    if path:
        return Path(path).read_text(encoding="utf-8").strip()
    return os.getenv("CRCON_RELEASES_GITHUB_TOKEN", "").strip()


def published_release(item):
    if not isinstance(item, dict) or item.get("draft") is not False:
        return False
    try:
        published = datetime.fromisoformat(item["published_at"].replace("Z", "+00:00"))
        return published <= datetime.now(timezone.utc) and parse_version(item.get("tag_name")) is not None
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def select_releases(catalog, installed):
    version = parse_version(installed)
    if not version:
        return []
    published = [r for r in catalog if published_release(r)]
    current = next((r for r in published if parse_version(r["tag_name"]) == version), None)
    if current is None:
        return []
    # History is the stable release history up to this installation, not an
    # assertion that every historical version was once installed here.
    history = [r for r in published if not r.get("prerelease")
               and parse_version(r["tag_name"])[1] is None
               and parse_version(r["tag_name"])[0] < version[0]
               and datetime.fromisoformat(r["published_at"].replace("Z", "+00:00"))
               <= datetime.fromisoformat(current["published_at"].replace("Z", "+00:00"))]
    history.sort(key=lambda r: parse_version(r["tag_name"])[0], reverse=True)
    result, seen = [], set()
    for item in [current, *history]:
        normalized = parse_version(item["tag_name"])
        if normalized in seen:
            continue
        seen.add(normalized)
        body, highlights = extract_highlights(str(item.get("body") or "")[:100_000])
        # Cached releases already have their editorial block removed.
        if highlights is None and not HIGHLIGHT_BLOCK.search(str(item.get("body") or "")):
            highlights = normalize_highlights(item.get("highlights"))
        result.append({
            "tag_name": item["tag_name"],
            "name": str(item.get("name") or item["tag_name"])[:300],
            "body": body,
            "highlights": highlights,
            "published_at": item["published_at"],
            "prerelease": bool(item.get("prerelease") or normalized[1]),
            "current": normalized == version,
        })
    return result[:30]


def get_channel(installed, frontend_version, cache):
    result = {"installed_version": installed, "frontend_version": frontend_version,
              "status": "unverified", "releases": [], "checked_at": None, "stale": False}
    current = parse_version(installed)
    if current is None or parse_version(frontend_version) is None:
        return result
    if current != parse_version(frontend_version):
        return {**result, "status": "version_mismatch"}
    try:
        token = release_token()
    except (OSError, ValueError):
        return {**result, "status": "unavailable"}
    if not token:
        # The normal private-repository deployment bundles a snapshot during
        # CI. GitHub's build credential is never copied into the image.
        try:
            snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
            releases = select_releases(snapshot["releases"], installed)
            return {**result, "releases": releases, "checked_at": snapshot["checked_at"],
                    "status": "ready" if releases else "no_release", "source": "bundled"}
        except (OSError, ValueError, TypeError, KeyError):
            return {**result, "status": "unavailable"}
    # Key includes the running version, so deployment/rollback never reuses a
    # different installation's already-filtered announcements.
    key = CACHE_KEY + installed
    try:
        snapshot = cache.get(key)
        if snapshot is None:
            previous = cache.get(key + ":previous")
            if not cache.add(key + ":lock", True, timeout=30):
                return {**result, "status": "unavailable"}
            try:
                catalog = []
                for page in range(1, 4):
                    batch = github_json(f"?per_page=100&page={page}", token)
                    if not isinstance(batch, list):
                        raise ValueError("Invalid release list")
                    catalog.extend(batch)
                    if len(batch) < 100:
                        break
                if not any(isinstance(r, dict) and parse_version(r.get("tag_name")) == current for r in catalog):
                    # Old deployments outside the bounded history still get
                    # their own release; never fall back to /latest.
                    try:
                        exact = github_json("/tags/" + quote(installed, safe=""), token)
                        catalog.append(exact)
                    except HTTPError as error:
                        if error.code != 404:
                            raise
                snapshot = {"releases": select_releases(catalog, installed),
                            "checked_at": datetime.now(timezone.utc).isoformat(), "stale": False}
                cache.set(key, snapshot, timeout=3600)
                cache.set(key + ":previous", snapshot, timeout=86400)
            except (OSError, ValueError, TypeError):
                snapshot = {**previous, "stale": True} if previous else {
                    "releases": [], "checked_at": None, "stale": True}
                cache.set(key, snapshot, timeout=120)
            finally:
                cache.delete(key + ":lock")
        # Reapply eligibility even to cached data (including after rollbacks).
        safe = select_releases([{**r, "draft": False} for r in snapshot["releases"]], installed)
        status = "ready" if safe else "unavailable" if snapshot["stale"] else "no_release"
        return {**result, **snapshot, "releases": safe, "status": status}
    except Exception:
        # Cache/network failures do not block CRCON. Never return error details
        # or log Requests, which can include an Authorization header.
        return {**result, "status": "unavailable"}
