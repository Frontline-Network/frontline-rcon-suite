"""Verify online HLL Vietnam Steam-to-EOS associations without guessing."""

from rcon.steam_utils import is_steam_id_64
from rcon.types import GameEnum


# Only these observed families establish the platform family of a roster row.
# Unknown or newly introduced platforms require a fresh read.
NON_STEAM_FAMILIES = frozenset({
    'eplatformfamily::xbox', 'eplatformfamily::xboxseries',
    'eplatformfamily::ps5', 'eplatformfamily::wingdk', 'eplatformfamily::egs',
})


def _non_steam_platform_id_is_safe(value):
    """Do not mistake opaque platform IDs for Steam64 associations.

    HLLV also fills the `steamId` field with platform-specific identifiers
    for non-Steam families. Values that could be a Steam64 ID, or are not
    strings, remain ambiguous and must fail closed.
    """
    return value is None or (isinstance(value, str) and not is_steam_id_64(value))


def verified_steam_id(rcon, player_id: str, player_info: dict | None) -> str | None:
    if (getattr(getattr(rcon, 'game_profile', None), 'game', None) != GameEnum.HLL_VIETNAM
            or not isinstance(player_info, dict)
            or player_info.get('player_id') != player_id
            or player_info.get('eos_id') != player_id
            or str(player_info.get('platform') or '').strip().lower() != 'eplatformfamily::steam'):
        return None
    steam_id = player_info.get('steam_id')
    if not isinstance(steam_id, str) or not is_steam_id_64(steam_id):
        return None
    if len(player_id) != 32 or not all(c in '0123456789abcdefABCDEF' for c in player_id):
        return None
    return steam_id


def prepare_online_identity_snapshot(rcon) -> dict:
    """Return one fresh, self-consistent HLLV roster keyed by EOS identity."""
    with rcon.without_retries():
        rows = rcon.get_all_player_info(strict=True, fresh=True)
    if not isinstance(rows, list):
        raise ValueError('Invalid player snapshot')
    players = {}
    seen_steam = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Invalid player snapshot row')
        eos = row.get('iD')
        if (not isinstance(eos, str) or len(eos) != 32
                or not all(c in '0123456789abcdefABCDEF' for c in eos)
                or row.get('eosId') != eos or eos in players):
            raise ValueError('Invalid or duplicate EOS identity in player snapshot')
        platform = str(row.get('platform') or '').strip().lower()
        steam = row.get('steamId')
        if platform == 'eplatformfamily::steam':
            details = {'player_id': eos, 'eos_id': row.get('eosId'),
                       'steam_id': steam, 'platform': row.get('platform')}
            if verified_steam_id(rcon, eos, details) is None or steam in seen_steam:
                raise ValueError('Invalid or duplicate Steam identity in player snapshot')
            seen_steam.add(steam)
        elif platform not in NON_STEAM_FAMILIES:
            raise ValueError('Unknown online platform in identity snapshot')
        else:
            # An opaque platform ID is not a verified Steam association.
            # A Steam64-shaped value is ambiguous and must still fail closed.
            if not _non_steam_platform_id_is_safe(steam):
                raise ValueError('Unexpected Steam identity on non-Steam platform')
            steam = None
        players[eos] = {'steam_id': steam, 'platform': platform}
    return players


def prepare_online_steam_identity(rcon, steam_id: str) -> dict:
    """Read a fresh roster; an absent account is not an invented EOS ID."""
    if not is_steam_id_64(steam_id):
        raise ValueError('Invalid Steam ID')
    with rcon.without_retries():
        # A silently skipped malformed player would make an online Steam ID
        # appear absent, potentially acknowledging an unenforced restriction.
        players = rcon.get_all_player_info(strict=True, fresh=True)
    if not isinstance(players, list):
        raise ValueError('Invalid player snapshot')
    matching = set()
    seen_eos = set()
    seen_steam = set()
    for row in players:
        if not isinstance(row, dict):
            raise ValueError('Invalid player snapshot row')
        eos = row.get('iD')
        if not isinstance(eos, str):
            raise ValueError('Player snapshot has no identity')
        details = {'player_id': eos, 'eos_id': row.get('eosId'),
                   'steam_id': row.get('steamId'), 'platform': row.get('platform')}
        platform = str(row.get('platform') or '').strip().lower()
        if platform == 'eplatformfamily::steam':
            if verified_steam_id(rcon, eos, details) is None:
                raise ValueError('Incomplete online Steam identity')
        elif platform not in NON_STEAM_FAMILIES:
            raise ValueError('Unknown online platform in identity snapshot')
        elif not _non_steam_platform_id_is_safe(row.get('steamId')):
            raise ValueError('Inconsistent online Steam identity')
        if (len(eos) != 32 or not all(c in '0123456789abcdefABCDEF' for c in eos)
                or row.get('eosId') != eos or eos in seen_eos):
            raise ValueError('Invalid or duplicate EOS identity in player snapshot')
        seen_eos.add(eos)
        if platform == 'eplatformfamily::steam':
            if row['steamId'] in seen_steam:
                raise ValueError('Multiple online EOS IDs for one Steam ID')
            seen_steam.add(row['steamId'])
        if row.get('steamId') == steam_id:
            if verified_steam_id(rcon, eos, details) != steam_id:
                raise ValueError('Inconsistent online Steam identity')
            matching.add(eos)
    if len(matching) > 1:
        raise ValueError('Multiple online EOS IDs for one Steam ID')
    return {'steam_id': steam_id, 'eos_id': next(iter(matching), None)}
