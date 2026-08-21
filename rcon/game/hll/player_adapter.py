"""HLL WW2 player-response adapter."""

from rcon.game.player_adapter import BasePlayerInfoAdapter


class HLLPlayerInfoAdapter(BasePlayerInfoAdapter):
    """Normalize the original HLL response spelling into the canonical DTO."""

    player_id_keys = ("iD", "playerId", "PlayerId", "id", "Id")
    eos_id_keys = ("eosId", "eosID", "eos_id")
