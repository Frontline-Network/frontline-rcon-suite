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


def test_ci_uses_truthy_stable_tag_not_falsy_empty_candidate_branch():
    workflow = (Path(__file__).parents[1] / ".github/workflows/docker-images.yml").read_text()
    assert "contains(github.ref_name, 'rc') && ''" not in workflow
    assert workflow.count("!contains(github.ref_name, 'rc') && format(") == 2
    # GitHub &&/|| is a short-circuit expression, not a ternary. An empty
    # true-branch falls through to the right-hand side, publishing latest.
    for is_candidate in (False, True):
        assert ((not is_candidate and "repository:latest") or "") == (
            "" if is_candidate else "repository:latest"
        )


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
