"""HLL Vietnam V2 player-response adapter."""

from rcon.game.player_adapter import BasePlayerInfoAdapter


class HLLVPlayerInfoAdapter(BasePlayerInfoAdapter):
    """Normalize the documented HLLV V2 response spelling into the shared DTO."""

    player_id_keys = ("iD", "playerId", "PlayerId", "id", "Id")
    # The HLLV protocol calls the EOS identifier ``Id``.  Prefer it over the
    # legacy HLL spelling while retaining that spelling for mixed-version hosts.
    eos_id_keys = ("id", "Id", "eosId", "eosID", "eos_id")
