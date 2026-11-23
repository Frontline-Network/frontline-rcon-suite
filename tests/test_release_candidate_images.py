"""No registry writes: prove pilot verification preserves the stable channel."""
import importlib.util
import json
from pathlib import Path
from unittest.mock import patch

import pytest

SPEC = importlib.util.spec_from_file_location(
    "verify_candidate_images", Path(__file__).parents[1] / "scripts/verify_release_images.py"
)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


@pytest.mark.parametrize(
    "version,latest,allowed",
    [
        ("v0.9.3-rc.1", "stable", True),
        ("v0.9.3-rc.1", "candidate", False),
        ("v0.9.3", "candidate", True),
        ("v0.9.3", "stable", False),
    ],
)
def test_release_tag_policy(version, latest, allowed):
    candidate = {"digest": "candidate"}
    with patch.object(verifier, "docker", side_effect=[json.dumps(candidate), json.dumps({"digest": latest})]):
        if allowed:
            result = verifier.verify_tags("example/image", version, candidate)
            assert result["prerelease"] == ("-rc." in version)
            assert result["latest_matches"] == (latest == "candidate")
        else:
            with pytest.raises(AssertionError):
                verifier.verify_tags("example/image", version, candidate)


def test_wrong_candidate_tag_is_rejected_before_latest_check():
    with patch.object(verifier, "docker", return_value=json.dumps({"digest": "other"})) as registry:
        with pytest.raises(AssertionError, match="does not match"):
            verifier.verify_tags("example/image", "v0.9.3-rc.1", {"digest": "candidate"})
    assert registry.call_count == 1


def test_only_verified_workflow_can_publish_stable_images():
    import yaml

    workflows = Path(__file__).parents[1] / ".github/workflows"
    jobs = yaml.safe_load((workflows / "docker-images.yml").read_text())["jobs"]
    for name in ("backend", "frontend"):
        push, = [step for step in jobs[name]["steps"] if step.get("with", {}).get("push")]
        assert ":latest" not in push["with"]["tags"]
        assert "needs.source.outputs.version" in push["with"]["tags"]
    verify = jobs["verify-published-images"]
    assert {"backend", "frontend"} <= set(verify["needs"])
    assert "needs.backend.result == 'success' && needs.frontend.result == 'success'" in verify["if"]
    assert "github.event_name == 'release'" not in verify["if"]
    assert all("continue-on-error" not in step for step in verify["steps"])
    assert any("playwright test" in step.get("run", "") for step in verify["steps"])
    promote = jobs["promote-stable"]
    assert "verify-published-images" in promote["needs"] and "always()" not in promote["if"]
    assert not promote["concurrency"]["cancel-in-progress"]
    assert promote["concurrency"]["group"] == jobs["restore-stable-latest"]["concurrency"]["group"]
    assert not promote.get("continue-on-error", False)
    assert "!github.event.release.prerelease" in promote["if"]
    for name, stable in [("docker-images-manual.yml", True), ("build-docker-images-manual-tag-only.yml", False)]:
        wrapper, = yaml.safe_load((workflows / name).read_text())["jobs"].values()
        assert wrapper["uses"] == "./.github/workflows/docker-images.yml"
        assert wrapper["with"]["publish_stable"] is stable


def test_stable_version_can_be_verified_before_latest_moves():
    candidate, old = {"digest": "candidate"}, {"digest": "old"}
    with patch.object(verifier, "docker", side_effect=[json.dumps(candidate), json.dumps(old)]):
        result = verifier.verify_tags("example/image", "v1.0.0", candidate, before_promotion=True)
    assert not result["latest_matches"]


@pytest.mark.parametrize("latest,allowed,writes", [("candidate", True, 1), ("stable", True, 0), ("other", False, 0)])
def test_latest_repair_is_idempotent_and_refuses_unrelated_release(latest, allowed, writes):
    spec = importlib.util.spec_from_file_location("restore_latest", Path(__file__).parents[1] / "scripts/restore_v092_latest.py")
    recovery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recovery)
    with patch.object(recovery, "inspect", side_effect=["stable", "candidate", "stable", latest, "stable", "candidate"]), patch.object(recovery.subprocess, "check_call") as publish:
        if allowed:
            recovery.restore("example/image", "stable-digest", "candidate-digest")
        else:
            with pytest.raises(AssertionError, match="Unrelated latest"):
                recovery.restore("example/image", "stable-digest", "candidate-digest")
        assert publish.call_count == writes
