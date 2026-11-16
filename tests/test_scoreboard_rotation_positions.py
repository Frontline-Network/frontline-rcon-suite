from types import SimpleNamespace

from rcon.maps import UNKNOWN_MAP_NAME
from rcon.scoreboard import build_map_rotation_embed, guess_current_map_rotation_positions, guess_next_map_rotation_positions


def rotation(*names):
    return [SimpleNamespace(id=name) for name in names]


def positions(maps, current, next_map):
    current_indices = guess_current_map_rotation_positions(maps, {'id': current}, {'id': next_map})
    return current_indices, guess_next_map_rotation_positions(current_indices, maps, {'id': next_map})


def test_duplicates_only_mark_matching_current_and_next_maps():
    assert positions(rotation('A', 'B', 'C', 'B', 'A'), 'A', 'B') == ([0], [1])


def test_server_next_map_override_is_not_replaced_by_rotation_successor():
    assert positions(rotation('A', 'B', 'C'), 'A', 'C') == ([0], [2])


def test_wraparound_single_map_and_unresolved_positions():
    assert positions(rotation('A', 'B', 'C'), 'C', 'A') == ([2], [0])
    assert positions(rotation('A'), 'A', 'A') == ([0], [0])
    assert positions(rotation('A', 'B', 'A', 'C'), 'A', 'X') == ([0, 2], [])
    assert positions(rotation(), 'A', 'B') == ([], [])
    assert positions(rotation('A', 'B', 'A', 'B'), 'A', 'B') == ([0, 2], [1, 3])
    assert positions(rotation('A', 'B'), 'A', UNKNOWN_MAP_NAME) == ([0], [])
    assert positions(rotation('A', 'B'), UNKNOWN_MAP_NAME, 'B') == ([], [1])


def test_embed_marks_server_reported_next_map():
    maps = [SimpleNamespace(id=name, pretty_name=name) for name in ('A', 'B', 'C')]
    api = SimpleNamespace(get_map_rotation=lambda: {'maps': maps},
        get_gamestate=lambda: {'current_map': {'id': 'A'}, 'next_map': {'id': 'C'}})
    config = SimpleNamespace(public_scoreboard_url='https://example.org/',
        map_rotation_include_server_name=False, map_rotation_title_text='Rotation',
        current_map_format='current {} {}', next_map_format='next {} {}',
        other_map_format='other {} {}', show_map_legend=False, footer_last_refreshed_text='updated')
    embed = build_map_rotation_embed(config, api, 'test')
    assert embed.fields[0]['value'] == 'current A 1\nother B 2\nnext C 3'
