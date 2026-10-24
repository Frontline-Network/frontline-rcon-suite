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
