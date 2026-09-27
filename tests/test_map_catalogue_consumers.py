"""Map consumers must retain the selected game's catalogue and game modes."""

import os
from unittest.mock import patch

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")

from rcon.game.hll.profile import HLL_PROFILE
from rcon.game.hllv.profile import HLLV_PROFILE
from rcon.game.hllv.legacy_layers import HLLV_LEGACY_LAYER_ALIASES
from rcon.message_variables import format_map_vote


@pytest.mark.parametrize("profile", [HLL_PROFILE, HLLV_PROFILE], ids=["hll", "hllv"])
def test_catalogue_layers_and_modes_round_trip(profile):
    for layer in profile.layers.values():
        if layer.id == "unknown":
            continue
        assert profile.parse_layer(layer.id) == layer
        assert profile.parse_game_mode(layer.game_mode.value) == layer.game_mode


@pytest.mark.parametrize("profile", [HLL_PROFILE, HLLV_PROFILE], ids=["hll", "hllv"])
@pytest.mark.parametrize(
    "format_type",
    [
        "line",
        "vertical",
        "max_length",
        "by_mod_line",
        "by_mod_vertical",
        "by_mod_split",
        "by_mod_vertical_all",
    ],
)
def test_map_vote_messages_retain_catalogue_names_and_modes(profile, format_type):
    # A single entry avoids line-wrapping differences and checks every layer,
    # including Conquest, environments and both Offensive attacking sides.
    with patch("rcon.message_variables.VoteMap") as vote_map:
        for layer in profile.layers.values():
            if layer.id == "unknown":
                continue
            vote_map.return_value.get_selection.return_value = [layer]
            assert layer.pretty_name in format_map_vote(format_type), layer.id


@pytest.mark.parametrize(
    "readable,prefix",
    [
        ("cam_ranh_port", "wdeve"),
        ("dak_to_airfield", "wdevd"),
        ("hue_outskirts", "wdevc"),
        ("quang_ngai", "wdevb"),
        ("thanh_hoa_bridge", "wdevf"),
        ("van_tuong", "wdeva"),
    ],
)
@pytest.mark.parametrize(
    "mode", ["warfare", "domination", "conquest", "offensiveus", "offensivenva"]
)
@pytest.mark.parametrize("suffix", ["", "_day"])
def test_readable_hllv_aliases_resolve_to_known_layers(readable, prefix, mode, suffix):
    assert (
        HLLV_PROFILE.parse_layer(f"{readable}_{mode}{suffix}")
        == HLLV_PROFILE.layers[f"{prefix}_{mode}_day"]
    )


def test_all_hllv_aliases_resolve_to_their_canonical_layer():
    for alias, canonical in HLLV_LEGACY_LAYER_ALIASES.items():
        assert HLLV_PROFILE.parse_layer(alias) == HLLV_PROFILE.layers[canonical], alias
