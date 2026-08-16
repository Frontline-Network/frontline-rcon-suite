import os
from datetime import datetime, timezone

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.autobalancer.models import BalanceSnapshot, PlayerSnapshot, SkillRating
from rcon.autobalancer.planner import (
    build_plan,
    build_strategy_plans,
    protection_tier,
    required_switches,
)


def player(
    player_id,
    *,
    team="allies",
    role="rifleman",
    unit="able",
    unit_type="infantry",
    size=3,
    squad_seconds=600,
    connected_seconds=600,
    rating=50,
    leader=False,
):
    return PlayerSnapshot(
        player_id=player_id,
        name=player_id,
        team=team,
        role=role,
        unit_id=unit,
        unit_name=unit,
        unit_type=unit_type,
        unit_size=size,
        squad_seconds=squad_seconds,
        connected_seconds=connected_seconds,
        is_leader=leader,
        rating=SkillRating(value=rating, confidence=1),
    )


def snapshot(players, allies_count=50, axis_count=44):
    return BalanceSnapshot(
        round_id="1000:test",
        captured_at=datetime.now(timezone.utc),
        map_name="test",
        map_elapsed_seconds=900,
        time_remaining_seconds=3600,
        allies_count=allies_count,
        axis_count=axis_count,
        players=players,
    )


@pytest.mark.parametrize(
    "allies,axis,target,expected",
    [
        (50, 44, 2, 2),
        (49, 46, 2, 1),
        (41, 39, 2, 0),
        (50, 45, 2, 2),
        (44, 50, 2, 2),
        (50, 44, 0, 3),
    ],
)
def test_required_switches(allies, axis, target, expected):
    assert required_switches(allies - axis, target) == expected


@pytest.mark.parametrize(
    "candidate,expected",
    [
        (player("unassigned", unit=None, size=0), 0),
        (player("solo", size=1), 0),
        (player("recent", size=4, squad_seconds=299), 1),
        (player("incomplete", size=4, squad_seconds=600), 2),
        (player("stable", size=4, squad_seconds=901), 3),
        (player("full", size=6), 3),
        (player("leader", role="officer", leader=True), 4),
        (player("armor", role="crewman", unit_type="armor"), 5),
        (player("recon", role="sniper", unit_type="recon"), 5),
        (player("arty", role="gunner", unit_type="artillery"), 5),
        (player("mortar", role="mortargunner", unit_type="mortar"), 5),
        (player("helicopter", role="helicopterpilot", unit_type="helicopter"), 5),
        (player("hllv-leader", role="squadleader", leader=True), 4),
    ],
)
def test_protection_tiers(candidate, expected):
    assert protection_tier(candidate)[0] == expected


def test_commander_is_hard_excluded_even_when_volunteering():
    commander = player("commander", role="armycommander", unit_type="commander")
    fallback = player("fallback", unit=None, size=0)
    plan = build_plan(snapshot([commander, fallback]), volunteers={"commander"})
    assert plan.candidates[0].player.player_id == "fallback"
    assert any("Commander" in reason for reason in plan.blocked_reasons)


def test_cooldown_and_recent_connection_are_hard_exclusions():
    protected = player("protected", unit=None, size=0)
    recent = player("recent", unit=None, size=0, connected_seconds=119)
    allowed = player("allowed", unit=None, size=0)
    plan = build_plan(
        snapshot([protected, recent, allowed]),
        cooldown_player_ids={"protected"},
    )
    assert [item.player.player_id for item in plan.candidates] == ["allowed"]


def test_volunteer_reduces_soft_tier_by_two():
    volunteer = player("volunteer", size=6)
    normal = player("normal", unit="baker", size=4, squad_seconds=600)
    plan = build_plan(snapshot([volunteer, normal]), volunteers={"volunteer"})
    assert plan.candidates[0].player.player_id == "volunteer"
    assert plan.candidates[0].base_tier == 3
    assert plan.candidates[0].effective_tier == 1


def test_multi_player_plan_uses_other_squad_when_equivalent():
    players = [
        player("a1", unit="able", unit_type="infantry", rating=40),
        player("a2", unit="able", unit_type="infantry", rating=45),
        player("b1", unit="baker", unit_type="infantry", rating=50),
        player("axis", team="axis", unit="dog", rating=55),
    ]
    plan = build_plan(snapshot(players), max_switches=3)
    assert len(plan.candidates) == 2
    assert len({candidate.player.squad_key for candidate in plan.candidates}) == 2


def test_multi_player_plan_optimizes_the_complete_rating_projection():
    players = [
        player("zero", unit="able", rating=0),
        player("thirty", unit="baker", rating=30),
        player("seventy", unit="charlie", rating=70),
        player("ninety", unit="dog", rating=90),
        player("axis", team="axis", unit="easy", rating=50),
    ]
    plan = build_plan(snapshot(players), max_switches=3)
    assert {candidate.player.player_id for candidate in plan.candidates} == {
        "zero",
        "ninety",
    }


def test_skill_only_balance_never_creates_a_plan():
    players = [
        player("strong", rating=100),
        player("weak", team="axis", rating=0),
    ]
    assert build_plan(snapshot(players, allies_count=40, axis_count=40)) is None


def test_odd_one_player_difference_never_creates_an_overshooting_candidate():
    plan = build_plan(
        snapshot([player("candidate")], allies_count=41, axis_count=40),
        target_difference=0,
    )
    assert plan is not None
    assert plan.candidates == []
    assert "nicht reduzieren" in plan.blocked_reasons[0]


def test_balanced_v2_may_use_exactly_one_higher_tier_for_clear_improvement():
    players = [
        player("low-tier", unit=None, size=0, rating=0),
        player("higher-tier", size=4, squad_seconds=299, rating=100),
        player(
            "fixed",
            role="armycommander",
            unit_type="commander",
            rating=100,
        ),
        player("axis", team="axis", rating=50),
    ]
    plans = build_strategy_plans(
        snapshot(players, allies_count=50, axis_count=47),
        skill_gap_soft_limit=8,
        skill_gap_min_improvement=2.5,
    )
    assert plans["squad-first"].candidates[0].player.player_id == "low-tier"
    assert plans["balanced-v2"].candidates[0].player.player_id == "higher-tier"
    assert plans["skill-first"].candidates[0].player.player_id == "higher-tier"


def test_balanced_v2_does_not_escalate_to_specialist_only_for_rating():
    players = [
        player("leader", role="officer", leader=True, rating=0),
        player("armor", role="crewman", unit_type="armor", rating=100),
        player(
            "fixed",
            role="armycommander",
            unit_type="commander",
            rating=100,
        ),
        player("axis", team="axis", rating=50),
    ]
    balanced = build_plan(
        snapshot(players, allies_count=50, axis_count=47),
        strategy="balanced-v2",
    )
    assert balanced.candidates[0].player.player_id == "leader"


def test_specialist_is_used_when_required_count_is_not_reachable_without_one():
    players = [
        player("leader", role="officer", leader=True, rating=40),
        player("armor", role="crewman", unit_type="armor", rating=60),
        player("axis", team="axis", rating=50),
    ]
    balanced = build_plan(
        snapshot(players, allies_count=50, axis_count=44),
        strategy="balanced-v2",
        max_switches=3,
    )
    assert {item.player.player_id for item in balanced.candidates} == {
        "leader",
        "armor",
    }


def test_hard_rating_warning_is_recorded_but_does_not_block_plan():
    players = [
        player("candidate", unit=None, rating=100),
        player(
            "fixed",
            role="armycommander",
            unit_type="commander",
            rating=100,
        ),
        player("axis", team="axis", rating=0),
    ]
    plan = build_plan(
        snapshot(players, allies_count=50, axis_count=47),
        strategy="balanced-v2",
        skill_gap_hard_warning=12,
    )
    assert plan.candidates
    assert plan.projected_rating_gap >= 12
    assert plan.warnings
