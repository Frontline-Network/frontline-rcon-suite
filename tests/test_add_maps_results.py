from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from rcon.commands import HLLCommandFailedError, ServerCtl
from rcon.rcon import Rcon


def test_empty_input_does_not_read_or_modify_the_server():
    rcon = Rcon.__new__(Rcon)
    with patch.object(Rcon, 'get_map_rotation') as read:
        assert rcon.add_maps_to_rotation([]) == []
        read.assert_not_called()


def test_success_returns_one_confirmed_result_for_each_insertion():
    rcon = Rcon.__new__(Rcon)
    with patch.object(Rcon, 'get_map_rotation', return_value={'maps': [SimpleNamespace(id='A')]}), \
         patch.object(ServerCtl, 'get_maps', return_value=['A', 'B']), \
         patch('rcon.rcon.invalidates', return_value=nullcontext()), \
         patch.object(ServerCtl, 'add_map_to_rotation_at_index') as add:
        assert rcon.add_maps_to_rotation(['B', 'B']) == [
            {'map_name': 'B', 'index': 1, 'status': 'confirmed'},
            {'map_name': 'B', 'index': 2, 'status': 'confirmed'},
        ]
    assert [call.args for call in add.call_args_list] == [('B', 1), ('B', 2)]


def test_invalid_map_is_rejected_before_any_mutation():
    rcon = Rcon.__new__(Rcon)
    with patch.object(Rcon, 'get_map_rotation', return_value={'maps': [SimpleNamespace(id='A')]}), \
         patch.object(ServerCtl, 'get_maps', return_value=['A', 'B']), \
         patch.object(ServerCtl, 'add_map_to_rotation_at_index') as add:
        with pytest.raises(HLLCommandFailedError, match='Maps not offered'):
            rcon.add_maps_to_rotation(['B', 'missing'])
    add.assert_not_called()


def test_partial_or_uncertain_failure_reports_observed_state_and_stops():
    rcon = Rcon.__new__(Rcon)
    with patch.object(Rcon, 'get_map_rotation', return_value={'maps': [SimpleNamespace(id='A')]}), \
         patch.object(ServerCtl, 'get_maps', return_value=['A', 'B', 'C', 'D']), \
         patch('rcon.rcon.invalidates', return_value=nullcontext()), \
         patch.object(ServerCtl, 'get_map_rotation', return_value={'maps': ['A', 'B']}), \
         patch.object(ServerCtl, 'add_map_to_rotation_at_index', side_effect=[None, TimeoutError('lost reply')]) as add:
        with pytest.raises(HLLCommandFailedError, match='observed after failure.*A.*B'):
            rcon.add_maps_to_rotation(['B', 'C', 'D'])
    assert add.call_count == 2
