from unittest.mock import patch

from rcon.commands import ServerCtl
from rcon.rcon import Rcon


def test_rejected_vip_removal_keeps_expiration_record():
    with patch.object(ServerCtl, "remove_vip", return_value=False), patch(
        "rcon.rcon.enter_session"
    ) as session:
        result = Rcon.remove_vip.__wrapped__(object.__new__(Rcon), "fake-player")
    assert result is False
    session.assert_not_called()
