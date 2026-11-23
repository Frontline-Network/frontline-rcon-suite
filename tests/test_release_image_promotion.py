from unittest.mock import Mock

import pytest

from scripts import promote_release_images as release


VERSION = "v0.9.13"
NEW = {"backend": "sha256:" + "1" * 64, "frontend": "sha256:" + "2" * 64}
OLD = {"backend": "sha256:" + "3" * 64, "frontend": "sha256:" + "4" * 64}


@pytest.fixture
def registry(monkeypatch):
    tags = {repo + ":" + VERSION: digest for repo, digest in NEW.items()}
    tags.update({repo + ":latest": digest for repo, digest in OLD.items()})
    write = Mock(side_effect=lambda repo, digest: tags.update({repo + ":latest": digest}))
    monkeypatch.setattr(release, "digest_of", tags.__getitem__)
    monkeypatch.setattr(release, "tag_latest", write)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    return tags, write


def test_promotes_exact_verified_digests_once(registry):
    tags, write = registry
    release.promote(VERSION, NEW)
    release.promote(VERSION, NEW)
    assert write.call_count == 2
    assert all(tags[repo + ":latest"] == digest == tags[repo + ":" + VERSION] for repo, digest in NEW.items())


@pytest.mark.parametrize("version", ["latest", "v0.9.13-rc.1", "v0.9.13-beta.1"])
def test_nonstable_versions_cannot_promote(registry, version):
    with pytest.raises(ValueError):
        release.promote(version, NEW)
    registry[1].assert_not_called()


def test_version_moved_before_promotion(registry):
    tags, write = registry
    tags["frontend:" + VERSION] = OLD["frontend"]
    with pytest.raises(RuntimeError, match="moved"):
        release.promote(VERSION, NEW)
    write.assert_not_called()


@pytest.mark.parametrize("failed", ["backend", "frontend"])
@pytest.mark.parametrize("accepted_before_failure", [False, True])
def test_rollback_after_registry_failure(registry, failed, accepted_before_failure):
    tags, write = registry
    def store(repo, digest):
        failing = repo == failed and digest == NEW[repo]
        if not failing or accepted_before_failure:
            tags[repo + ":latest"] = digest
        if failing:
            raise OSError("registry failure")
    write.side_effect = store
    with pytest.raises(OSError):
        release.promote(VERSION, NEW)
    assert all(tags[repo + ":latest"] == digest for repo, digest in OLD.items())


def test_rollback_preserves_unrelated_registry_change(registry):
    tags, write = registry
    unrelated = "sha256:" + "a" * 64
    def store(repo, digest):
        if repo == "frontend":
            tags["backend:latest"] = unrelated
            raise OSError("registry failure")
        tags["backend:latest"] = digest
    write.side_effect = store
    with pytest.raises(RuntimeError, match="rollback requires review"):
        release.promote(VERSION, NEW)
    assert tags["backend:latest"] == unrelated
    assert tags["frontend:latest"] == OLD["frontend"]
