import pytest

from rcon.game.hll.profile import HLL_PROFILE
from rcon.game.hllv.profile import HLLV_PROFILE
from rconweb.api.capabilities import (
    CAPABILITIES_SCHEMA_VERSION,
    OPERATION_REQUIREMENTS,
    build_capabilities,
)


ALL_REGISTERED_COMMANDS = {
    command
    for requirements in OPERATION_REQUIREMENTS.values()
    for command in requirements
}


@pytest.mark.parametrize(
    ("profile", "expected_modes", "expected_warmup_modes"),
    [
        (HLL_PROFILE, {"warfare", "offensive", "conquest", "skirmish", "phased", "majority"}, {"warfare", "skirmish"}),
        (HLLV_PROFILE, {"warfare", "offensive", "conquest", "domination"}, {"warfare"}),
    ],
)
def test_capabilities_describe_the_active_game_without_rcon_io(
    profile, expected_modes, expected_warmup_modes
):
    contract = build_capabilities(profile, ALL_REGISTERED_COMMANDS)

    assert contract["schema_version"] == CAPABILITIES_SCHEMA_VERSION
    assert contract["game"]["id"] == profile.game.value
    assert set(contract["game"]["supported_game_modes"]) == expected_modes
    assert contract["game"]["sector_layout"] == {
        "read": True,
        "set": True,
        "remove": False,
    }
    assert set(contract["game"]["timer_controls"]["warmup_timer_modes"]) == expected_warmup_modes
    assert all(item["available"] for item in contract["operations"].values())


def test_capabilities_never_advertise_a_partial_operation():
    commands_without_temp_ban = ALL_REGISTERED_COMMANDS - {"temp_ban"}

    contract = build_capabilities(HLL_PROFILE, commands_without_temp_ban)

    assert contract["operations"]["player_moderation"] == {
        "available": False,
        "required_legacy_commands": ["punish", "kick", "temp_ban", "perma_ban"],
    }


def test_capabilities_keep_documented_versioned_entrypoints():
    contract = build_capabilities(HLL_PROFILE, ALL_REGISTERED_COMMANDS)

    assert contract["interfaces"]["capabilities"] == {
        "version": "v1",
        "path": "/api/v1/capabilities",
        "methods": ["GET"],
        "authentication": "none",
    }
    assert contract["interfaces"]["legacy_api"]["documentation_path"] == "/api/get_api_documentation"
