import pytest

from rcon.automods.geofence import (
    is_outside_combat_area,
    is_spawned,
    normalize_world_position,
)


def test_normalizes_valid_world_position():
    assert normalize_world_position({"x": "1.5", "y": 2, "z": -3}) == (
        1.5,
        2.0,
        -3.0,
    )


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        {"x": 1, "y": 2},
        {"x": "unknown", "y": 2, "z": 3},
        {"x": float("inf"), "y": 2, "z": 3},
    ],
)
def test_rejects_unusable_world_position(raw):
    assert normalize_world_position(raw) is None


def test_zero_position_is_not_spawned():
    assert is_spawned((0.0, 0.0, 0.0)) is False
    assert is_spawned((0.0, 0.0, 1.0)) is True


@pytest.mark.parametrize(
    ("position", "team", "expected"),
    [
        ((20_159.0, 0.0, 1.0), "allies", False),
        ((20_160.0, 0.0, 1.0), "allies", True),
        ((-20_160.0, 0.0, 1.0), "axis", False),
        ((-20_161.0, 0.0, 1.0), "axis", True),
    ],
)
def test_carentan_uses_map_specific_horizontal_boundaries(
    position, team, expected
):
    assert (
        is_outside_combat_area(
            position, map_id="carentan", team=team, max_caps=3
        )
        is expected
    )


@pytest.mark.parametrize(
    ("max_caps", "x_coordinate", "expected"),
    [
        (2, -20_161.0, False),
        (2, -20_160.0, True),
        (4, 60_479.0, False),
        (4, 60_480.0, True),
    ],
)
def test_boundary_tracks_configured_sector_limit(max_caps, x_coordinate, expected):
    assert (
        is_outside_combat_area(
            (x_coordinate, 0.0, 1.0),
            map_id="carentan",
            team="allies",
            max_caps=max_caps,
        )
        is expected
    )


@pytest.mark.parametrize(
    ("position", "team", "expected"),
    [
        ((0.0, -19_840.0, 1.0), "allies", False),
        ((0.0, -19_841.0, 1.0), "allies", True),
        ((0.0, 19_839.0, 1.0), "axis", False),
        ((0.0, 19_840.0, 1.0), "axis", True),
    ],
)
def test_foy_uses_vertical_attack_direction(position, team, expected):
    assert (
        is_outside_combat_area(position, map_id="foy", team=team, max_caps=3)
        is expected
    )


@pytest.mark.parametrize(
    ("position", "team", "expected"),
    [
        ((-19_841.0, 0.0, 1.0), "allies", True),
        ((19_840.0, 0.0, 1.0), "axis", True),
    ],
)
def test_vietnam_maps_use_their_attack_direction(position, team, expected):
    assert (
        is_outside_combat_area(
            position, map_id="WDEV_A", team=team, max_caps=3
        )
        is expected
    )


def test_unknown_map_requests_fallback_detection():
    assert (
        is_outside_combat_area(
            (50_000.0, 0.0, 1.0),
            map_id="not-a-real-map",
            team="allies",
            max_caps=3,
        )
        is None
    )
