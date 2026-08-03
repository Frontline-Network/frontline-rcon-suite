import os

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rconweb.api.autobalancer import validate_shadow_review


def test_shadow_review_accepts_preferred_strategy_and_player():
    result = validate_shadow_review(
        {
            "decision_id": "decision-1",
            "verdict": "rejected",
            "category": "better_candidate",
            "comment": "Der Alternative folgen",
            "preferred_strategy": "balanced-v2",
            "preferred_player_id": "player-2",
        }
    )
    assert result == (
        "decision-1",
        "rejected",
        "better_candidate",
        "Der Alternative folgen",
        "balanced-v2",
        "player-2",
    )


def test_shadow_review_rejects_unknown_strategy():
    with pytest.raises(ValueError, match="preferred_strategy"):
        validate_shadow_review(
            {
                "decision_id": "decision-1",
                "verdict": "accepted",
                "preferred_strategy": "random",
            }
        )
