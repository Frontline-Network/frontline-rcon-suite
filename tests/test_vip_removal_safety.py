from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from rcon.commands import HLLCommandFailedError, ServerCtl
from rcon.rcon import Rcon
from rcon.types import GameEnum


def test_rejected_vip_removal_keeps_expiration_record():
    api = object.__new__(Rcon)
    api.config = SimpleNamespace(game=GameEnum.HLL_WW2)
    with (
        patch("rcon.vip_rewards.locking.vip_lock", return_value=nullcontext()),
        patch.object(ServerCtl, "get_vip_ids") as lookup,
        patch.object(ServerCtl, "remove_vip", return_value=False),
        patch("rcon.rcon.enter_session") as session,
    ):
        result = api.remove_vip("fake-player")
    assert result is False
    lookup.assert_not_called()
    session.assert_not_called()


@pytest.mark.parametrize("rows", [None, {}, "", [{}], [{"iD": "", "comment": "Unknown"}]])
def test_malformed_vietnam_membership_is_not_an_empty_list(rows):
    api = object.__new__(Rcon)
    api.config = SimpleNamespace(game=GameEnum.HLL_VIETNAM)
    with (
        patch("rcon.vip_rewards.locking.vip_lock", return_value=nullcontext()),
        patch.object(ServerCtl, "exchange", return_value=SimpleNamespace(content_dict={"vipPlayers": rows})),
        patch.object(ServerCtl, "remove_vip") as remove,
        patch("rcon.rcon.enter_session") as session,
        pytest.raises(HLLCommandFailedError),
    ):
        api.remove_vip("fictional-player")
    remove.assert_not_called()
    session.assert_not_called()
