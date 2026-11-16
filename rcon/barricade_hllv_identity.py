"""Verify online HLL Vietnam Steam-to-EOS associations without guessing."""

from rcon.steam_utils import is_steam_id_64
from rcon.types import GameEnum


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


def prepare_online_steam_identity(rcon, steam_id: str) -> dict:
    """Read a fresh roster; an absent account is not an invented EOS ID."""
    if not is_steam_id_64(steam_id):
        raise ValueError('Invalid Steam ID')
    rcon.get_raw_player_snapshot.clear_for()
    with rcon.without_retries():
        players = rcon.get_all_player_info()
    if not isinstance(players, list):
        raise ValueError('Invalid player snapshot')
    matching = set()
    for row in players:
        if not isinstance(row, dict):
            raise ValueError('Invalid player snapshot row')
        eos = row.get('iD')
        if not isinstance(eos, str):
            raise ValueError('Player snapshot has no identity')
        details = {'player_id': eos, 'eos_id': row.get('eosId'),
                   'steam_id': row.get('steamId'), 'platform': row.get('platform')}
        if row.get('steamId') == steam_id:
            if verified_steam_id(rcon, eos, details) != steam_id:
                raise ValueError('Inconsistent online Steam identity')
            matching.add(eos)
    if len(matching) > 1:
        raise ValueError('Multiple online EOS IDs for one Steam ID')
    return {'steam_id': steam_id, 'eos_id': next(iter(matching), None)}
