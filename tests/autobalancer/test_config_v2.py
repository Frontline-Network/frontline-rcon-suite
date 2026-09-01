import os

import pytest
from pydantic import ValidationError

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.user_config.autobalancer import AutobalancerUserConfig


def test_v2_shadow_calibration_defaults_are_safe():
    config = AutobalancerUserConfig()
    assert config.mode == "disabled"
    assert config.skill_strategy == "balanced-v2"
    assert config.skill_gap_soft_limit == 8
    assert config.skill_gap_hard_warning == 12
    assert config.skill_gap_min_improvement == 2.5
    assert config.history_half_life_days == 30
    assert config.coordinated_squad_switches_enabled is False
    assert config.allow_individual_squad_fallback is True


def test_hard_warning_must_not_be_below_soft_limit():
    with pytest.raises(ValidationError, match="hard_warning"):
        AutobalancerUserConfig(
            skill_gap_soft_limit=12,
            skill_gap_hard_warning=8,
        )


def test_skill_first_cannot_be_selected_as_executable_strategy():
    with pytest.raises(ValidationError):
        AutobalancerUserConfig(skill_strategy="skill-first")
