import pytest

from rcon.game.hll.profile import HLL_PROFILE
from rcon.game.hllv.profile import HLLV_PROFILE
from rcon.maps import Team
from rcon.player_stats import _resolve_map_stat_team


@pytest.mark.parametrize(
    ("profile", "layer_id"),
    [
        (HLL_PROFILE, "carentan_warfare"),
        (HLLV_PROFILE, "wdeva_warfare_day"),
    ],
)
def test_profiles_resolve_persisted_side_ids_without_hll_enum_assumptions(
    profile, layer_id
):
    layer = profile.parse_layer(layer_id)

    assert profile.team_id_for("allies") == 1
    assert profile.team_id_for("axis") == 2
    assert profile.team_for_id(1) is Team.ALLIES
    assert profile.team_for_id(2) is Team.AXIS
    assert _resolve_map_stat_team(
        game_profile=profile, map_layer=layer, persisted_team_id=1
    ) == ("allies", layer.map.allies.name.lower())
    assert _resolve_map_stat_team(
        game_profile=profile, map_layer=layer, persisted_team_id=2
    ) == ("axis", layer.map.axis.name.lower())


@pytest.mark.parametrize("unknown", [None, "north", 0, 6, -111, object()])
def test_profiles_keep_unknown_or_transition_teams_unassigned(unknown):
    layer = HLLV_PROFILE.parse_layer("wdeva_warfare_day")

    assert HLLV_PROFILE.team_for_id(unknown) is None
    assert _resolve_map_stat_team(
        game_profile=HLLV_PROFILE, map_layer=layer, persisted_team_id=unknown
    ) == (None, None)
