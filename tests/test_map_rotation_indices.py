from types import SimpleNamespace
from unittest.mock import patch

import pytest

from rcon.commands import ServerCtl
from rcon.rcon import Rcon


@pytest.mark.parametrize(
    "rotation,sequence,current,expected",
    [
        (["A", "B", "C"], ["C", "A", "B"], 0, (2, 0)),
        (["A", "B", "C"], ["C", "A", "B"], 2, (1, 2)),
        (["A", "A", "B"], ["A", "A", "B"], 0, (0, 1)),
        (["A", "A", "B"], ["B", "A"], 0, (2, None)),
        (["A", "B"], ["C", "A"], 0, (None, 0)),
        (["A"], [], 0, (None, None)),
        (["A"], ["A"], -1, (None, None)),
        (["A"], ["A"], 1, (None, None)),
        (["A"], ["/game/A"], 0, (0, 0)),
    ],
)
def test_rotation_indices_address_rotation_and_do_not_guess_duplicates(
    rotation, sequence, current, expected
):
    rcon = Rcon.__new__(Rcon)
    rcon.game_profile = SimpleNamespace(parse_layer=lambda name: SimpleNamespace(id=name))
    with patch.object(ServerCtl, "get_map_rotation", return_value={"maps": rotation, "current_index": 0}), \
         patch.object(ServerCtl, "get_map_sequence", return_value={"maps": sequence, "current_index": current}):
        result = Rcon.get_map_rotation.__wrapped__(rcon)
    assert [layer.id for layer in result["maps"]] == rotation
    assert (result["current_index"], result["next_index"]) == expected
