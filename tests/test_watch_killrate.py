from collections import Counter

from rcon.watch_killrate import (
    ARMOR,
    ARTILLERY,
    MGS,
    aggregate_weapon_kills,
)


def test_weapon_categories_are_aggregated_in_one_pass_without_changing_totals():
    weapons = Counter(
        {
            "M1 GARAND": 5,
            next(iter(ARMOR)): 7,
            next(iter(ARTILLERY)): 11,
            next(iter(MGS)): 13,
        }
    )

    assert aggregate_weapon_kills(weapons) == (5, 7, 11, 13)


def test_unknown_weapons_remain_part_of_base_kpm():
    assert aggregate_weapon_kills(Counter({"future HLLV weapon": 4})) == (
        4,
        0,
        0,
        0,
    )
