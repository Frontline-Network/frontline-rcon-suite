"""No peer may silently inherit another integration's delivery history."""
import pytest

from rcon.barricade_scan_identity import parse_integration_id

FIRST = '01234567-89ab-4def-8012-0123456789ab'
SECOND = '11234567-89ab-4def-8012-0123456789ab'


def test_explicit_peer_ids_are_stable_and_distinct():
    query = f'frontline_integration={FIRST}'.encode()
    first = parse_integration_id(query)
    assert first == parse_integration_id(query)
    assert first != parse_integration_id(f'frontline_integration={SECOND}'.encode())
    assert 'Bearer' not in first


@pytest.mark.parametrize('query', [b'', b'frontline_integration=', b'frontline_integration=not-a-uuid',
    f'frontline_integration={FIRST}&frontline_integration={FIRST}'.encode(),
    f'frontline_integration={FIRST.upper()}'.encode(), b'\xff', b'x=' + b'a' * 2049])
def test_missing_malformed_and_ambiguous_identity_is_not_guessed(query):
    assert parse_integration_id(query) is None
