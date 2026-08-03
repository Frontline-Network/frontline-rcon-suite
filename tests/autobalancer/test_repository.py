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
        "rating_model_version": "role-aware-v2",
        "strategy_version": "balanced-v2",
        "review_verdict": verdict,
        "review_category": category,
        "review_comment": None,
        "reviewed_by": "admin" if verdict else None,
        "reviewed_at": datetime(2026, 8, 3, 21, number % 60) if verdict else None,
        "reason": {
            "selection": "Mitglied eines unvollständigen Infantry-Squads",
            "plan": {
                "required_switches": 2,
                "rating_gap_before": 3.0,
                "projected_rating_gap": 1.25,
                "candidates": [
                    {
                        "player_id": player_id,
                        "projected_rating_gap": 1.25,
                    }
                ],
            },
            "strategies": {
                strategy: {
                    "rating_gap_before": 3.0,
                    "projected_rating_gap": gap,
                    "candidates": [
                        {
                            "player_id": player_id,
                            "player_name": f"Player {number}",
                            "base_tier": 2,
                            "effective_tier": 2,
                        }
                    ],
                    "warnings": [],
                }
                for strategy, gap in (
                    ("squad-first", 1.5),
                    ("balanced-v2", 1.25),
                    ("skill-first", 0.75),
                )
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
                    "rating": {
                        "version": "role-aware-v2",
                        "value": 55.0,
                        "raw_value": 58.0,
                        "confidence": 0.6,
                        "role_family": "combat_infantry",
                        "history_source": "exact_role",
                    },
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
    assert result["decisions"][0]["rating_raw"] == 58.0
    assert result["decisions"][0]["strategies_agree"] is True
    assert summary["strategy_agreement_rate"] == 1.0
    assert summary["gap_guardrail_rate"] == 1.0


def test_shadow_summary_detects_commander_rule_warning():
    result = summarize_shadow_decisions([decision(1, role="armycommander")])

    assert result["summary"]["rule_warning_proposals"] == 1
    assert "Commander" in result["decisions"][0]["audit_warnings"][0]
    assert result["pilot_goals"]["hard_rules_clean"] is False
    assert result["pilot_goals"]["ready_for_manual"] is False


def test_shadow_summary_detects_simulated_team_size_overshoot():
    item = decision(1)
    item["before_snapshot"]["allies_count"] = 41
    item["before_snapshot"]["axis_count"] = 40
    result = summarize_shadow_decisions([item])
    assert result["summary"]["size_overshoot_proposals"] == 1
    assert result["pilot_goals"]["no_size_overshoot"] is False
    assert any(
        "nicht reduzieren" in warning
        for warning in result["decisions"][0]["audit_warnings"]
    )


def test_shadow_pilot_goal_requires_twenty_proposals_and_ten_reviewed_rounds():
    result = summarize_shadow_decisions(
        [decision(number, "accepted") for number in range(20)]
    )

    assert result["summary"]["reviewed_rounds"] == 20
    assert result["summary"]["reviewed"] == 20
    assert result["summary"]["acceptance_rate"] == 1.0
    assert result["pilot_goals"]["reviewed_rounds_met"] is True
    assert result["pilot_goals"]["reviewed_proposals_met"] is True
    assert result["pilot_goals"]["acceptance_rate_met"] is True
    assert result["pilot_goals"]["rating_confidence_met"] is True
    assert result["pilot_goals"]["gap_guardrail_met"] is True
    assert result["pilot_goals"]["ready_for_manual"] is True


def test_ten_reviews_are_not_enough_for_v2_calibration():
    result = summarize_shadow_decisions(
        [decision(number, "accepted") for number in range(10)]
    )
    assert result["pilot_goals"]["reviewed_rounds_met"] is True
    assert result["pilot_goals"]["reviewed_proposals_met"] is False
    assert result["pilot_goals"]["ready_for_manual"] is False
