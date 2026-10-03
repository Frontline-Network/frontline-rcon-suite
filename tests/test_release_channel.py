import importlib.util
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("release_channel", Path(__file__).parents[1] / "rcon/release_channel.py")
channel = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(channel)


def release(tag, **extra):
    return {"tag_name": tag, "name": tag, "body": "## Changes\nRelease notes",
            "draft": False, "prerelease": False, "published_at": "2020-01-01T00:00:00Z", **extra}


class MemoryCache:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, timeout=None):
        self.values[key] = value

    def add(self, key, value, timeout=None):
        if key in self.values:
            return False
        self.set(key, value)
        return True

    def delete(self, key):
        self.values.pop(key, None)


class ReleaseChannelTests(TestCase):
    def test_newer_drafts_and_other_prereleases_are_never_announced(self):
        catalog = [release("v0.8.10"), release("v0.8.9"), release("v0.8.8"),
                   release("v0.8.7"), release("v0.8.6", draft=True),
                   release("v0.8.5-rc.2", prerelease=True)]
        self.assertEqual([r["tag_name"] for r in channel.select_releases(catalog, "v0.8.8")], ["v0.8.8", "v0.8.7"])

    def test_numeric_order_across_minor_and_major_boundaries(self):
        catalog = [release(v) for v in ("v1.0.0", "v0.10.0", "v0.9.12", "v0.9.9", "v0.8.10")]
        self.assertEqual([r["tag_name"] for r in channel.select_releases(catalog, "0.10.0")], ["v0.10.0", "v0.9.12", "v0.9.9", "v0.8.10"])

    def test_unknown_development_and_unpublished_installed_version_fail_closed(self):
        for version in ("unknown", "development", "latest", "v0.8.8-2-gabc", "v0.8.8+local", "v0.8.9"):
            with self.subTest(version=version):
                self.assertEqual(channel.select_releases([release("v0.8.8")], version), [])

    def test_only_installed_prerelease_is_included(self):
        catalog = [release("v0.8.9"), release("v0.8.9-rc.2", prerelease=True),
                   release("v0.8.9-rc.1", prerelease=True), release("v0.8.8")]
        self.assertEqual([r["tag_name"] for r in channel.select_releases(catalog, "v0.8.9-rc.1")], ["v0.8.9-rc.1", "v0.8.8"])

    def test_later_backport_is_not_announced_on_an_older_installation(self):
        catalog = [release("v1.0.0", published_at="2020-01-01T00:00:00Z"),
                   release("v0.9.9", published_at="2020-02-01T00:00:00Z")]
        self.assertEqual([r["tag_name"] for r in channel.select_releases(catalog, "v1.0.0")], ["v1.0.0"])

    def test_future_publication_and_unpublished_notes_are_excluded(self):
        for published in (None, "invalid", "2999-01-01T00:00:00Z", "2020-01-01"):
            self.assertEqual(channel.select_releases([release("v0.8.8", published_at=published)], "v0.8.8"), [])

    def test_response_contains_no_github_metadata_urls_or_credentials(self):
        result = channel.select_releases([release("v0.8.8", html_url="https://private", author={"login": "owner"}, assets=[{}], token="secret")], "v0.8.8")[0]
        self.assertEqual(set(result), {"tag_name", "name", "body", "published_at", "prerelease", "current"})

    def test_incomplete_rollout_and_unknown_frontend_never_fetch_source(self):
        with patch.object(channel, "release_token", side_effect=AssertionError("must not read source")):
            for frontend, expected in (("v0.8.7", "version_mismatch"), ("unknown", "unverified")):
                result = channel.get_channel("v0.8.8", frontend, MemoryCache())
                self.assertEqual(result["status"], expected)
                self.assertEqual(result["releases"], [])

    def test_bundled_private_notes_work_without_runtime_github_credentials(self):
        snapshot = {"checked_at": "2020-01-01", "releases": [release("v0.8.9"), release("v0.8.8"), release("v0.8.7")]}
        with patch.object(channel, "release_token", return_value=""), patch.object(Path, "read_text", return_value=json.dumps(snapshot)), patch.object(channel, "github_json", side_effect=AssertionError("offline snapshot")):
            current = channel.get_channel("v0.8.8", "0.8.8", MemoryCache())
            rollback = channel.get_channel("v0.8.7", "v0.8.7", MemoryCache())
        self.assertEqual(current["releases"][0]["tag_name"], "v0.8.8")
        self.assertEqual([r["tag_name"] for r in rollback["releases"]], ["v0.8.7"])

    def test_cache_is_scoped_to_installed_version_and_not_client_parameter(self):
        cache = MemoryCache()
        catalog = [release("v0.8.8"), release("v0.8.7")]
        with patch.object(channel, "release_token", return_value="test-only"), patch.object(channel, "github_json", return_value=catalog) as fetch:
            first = channel.get_channel("v0.8.8", "v0.8.8", cache)
            again = channel.get_channel("v0.8.8", "v0.8.8", cache)
            self.assertEqual(fetch.call_count, 1)
            rollback = channel.get_channel("v0.8.7", "v0.8.7", cache)
        self.assertEqual(first["releases"], again["releases"])
        self.assertEqual([r["tag_name"] for r in rollback["releases"]], ["v0.8.7"])

    def test_outage_preserves_only_previously_verified_version(self):
        cache = MemoryCache()
        with patch.object(channel, "release_token", return_value="test-only"), patch.object(channel, "github_json", return_value=[release("v0.8.8")]):
            channel.get_channel("v0.8.8", "v0.8.8", cache)
        cache.delete(channel.CACHE_KEY + "v0.8.8")
        with patch.object(channel, "release_token", return_value="test-only"), patch.object(channel, "github_json", side_effect=OSError("private details")):
            old = channel.get_channel("v0.8.8", "v0.8.8", cache)
            new = channel.get_channel("v0.8.9", "v0.8.9", cache)
        self.assertTrue(old["stale"])
        self.assertEqual(old["status"], "ready")
        self.assertEqual(new["releases"], [])
        self.assertNotIn("private details", json.dumps(new))

    def test_github_pagination_is_followed_but_bounded(self):
        with patch.object(channel, "release_token", return_value="test-only"), patch.object(channel, "github_json", side_effect=[[release("v0.9.0")] * 100, [release("v0.8.8")]]) as fetch:
            result = channel.get_channel("v0.8.8", "v0.8.8", MemoryCache())
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(len(result["releases"]), 1)

    def test_redirects_cannot_forward_github_credential(self):
        self.assertIsNone(channel.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example"))
