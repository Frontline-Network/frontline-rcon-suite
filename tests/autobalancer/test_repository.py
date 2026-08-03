from datetime import datetime

import pytest

from rcon.autobalancer.repository import summarize_shadow_decisions


def decision(
    number: int,
    verdict: str | None = None,
    category: str | None = None,
    role: str = "rifleman",
) -> dict:
    player_id = f"player-{number}"
    return {
        "decision_id": f"decision-{number}",
        "incident_id": f"incident-{number}",
        "round_id": f"round-{number}",
        "created_at": datetime(2026, 8, 3, 20, number % 60),
        "mode": "shadow",
        "source_team": "allies",
        "target_team": "axis",
        "player_id": player_id,
        "player_name": f"Player {number}",
        "volunteer": False,
        "protection_tier": 2,
        "rating": 55.0,
        "rating_confidence": 0.6,
        "review_verdict": verdict,
        "review_category": category,
        "review_comment": None,
        "reviewed_by": "admin" if verdict else None,
        "reviewed_at": datetime(2026, 8, 3, 21, number % 60) if verdict else None,
        "reason": {
            "selection": "Mitglied eines unvollständigen Infantry-Squads",
            "plan": {
                "required_switches": 2,
                "candidates": [
                    {
                        "player_id": player_id,
                        "projected_rating_gap": 1.25,
                    }
                ],
            },
        },
        "before_snapshot": {
            "map_name": "SME Warfare",
            "allies_count": 50,
            "axis_count": 44,
            "counts_match": True,
            "fail_count": 0,
            "stable_map": True,
            "players": [
                {
                    "player_id": player_id,
                    "name": f"Player {number}",
                    "team": "allies",
                    "role": role,
                    "unit_name": "Able",
                    "unit_type": "infantry",
                    "unit_size": 4,
                    "is_leader": False,
                    "connected_seconds": 900,
                    "squad_seconds": 400,
                }
            ],
        },
    }


def test_shadow_summary_reports_reviews_and_rejection_reasons():
    result = summarize_shadow_decisions(
        [
            decision(1, "accepted"),
            decision(2, "rejected", "better_candidate"),
            decision(3),
        ]
    )

    summary = result["summary"]
    assert summary["proposals"] == 3
    assert summary["reviewed"] == 2
    assert summary["pending_review"] == 1
    assert summary["accepted"] == 1
    assert summary["rejected"] == 1
    assert summary["acceptance_rate"] == pytest.approx(0.5)
    assert summary["reviewed_rounds"] == 2
    assert summary["rejection_categories"] == {"better_candidate": 1}
    assert summary["protection_tiers"] == {"2": 3}
    assert summary["average_rating_confidence"] == pytest.approx(0.6)
    assert result["decisions"][0]["projected_rating_gap"] == 1.25


def test_shadow_summary_detects_commander_rule_warning():
    result = summarize_shadow_decisions([decision(1, role="armycommander")])

    assert result["summary"]["rule_warning_proposals"] == 1
    assert "Commander" in result["decisions"][0]["audit_warnings"][0]
    assert result["pilot_goals"]["hard_rules_clean"] is False
    assert result["pilot_goals"]["ready_for_manual"] is False


def test_shadow_pilot_goal_requires_ten_reviewed_rounds_and_ninety_percent():
    result = summarize_shadow_decisions(
        [decision(number, "accepted") for number in range(10)]
    )

    assert result["summary"]["reviewed_rounds"] == 10
    assert result["summary"]["acceptance_rate"] == 1.0
    assert result["pilot_goals"]["reviewed_rounds_met"] is True
    assert result["pilot_goals"]["acceptance_rate_met"] is True
    assert result["pilot_goals"]["ready_for_manual"] is True
