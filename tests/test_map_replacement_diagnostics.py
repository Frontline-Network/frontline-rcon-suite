from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon.commands import HLLCommandFailedError, ServerCtl
from rcon.rcon import HLLRcon, HLLVRcon
from rcon.types import GameEnum, ServerInfo


@pytest.mark.parametrize("ctl_type,game", [(HLLRcon, GameEnum.HLL_WW2), (HLLVRcon, GameEnum.HLL_VIETNAM)])
@pytest.mark.parametrize("kind", ["rotation", "sequence"])
def test_unavailable_map_is_rejected_before_changes(monkeypatch, ctl_type, game, kind):
    ctl = ctl_type(ServerInfo(game=game))
    setattr(ctl, f"get_map_{kind}", Mock(return_value={"maps": [SimpleNamespace(id="old")]}))
    monkeypatch.setattr(ServerCtl, "get_maps", Mock(return_value=["valid"]))
    add = Mock()
    remove = Mock()
    monkeypatch.setattr(ServerCtl, f"add_map_to_{kind}_at_index", add)
    monkeypatch.setattr(ServerCtl, f"remove_map_from_{kind}_at_index", remove)

    with pytest.raises(HLLCommandFailedError, match="bad"):
        getattr(ctl, f"set_map_{kind}")(["valid", "bad"])
    add.assert_not_called()
    remove.assert_not_called()


@pytest.mark.parametrize("ctl_type,game", [(HLLRcon, GameEnum.HLL_WW2), (HLLVRcon, GameEnum.HLL_VIETNAM)])
@pytest.mark.parametrize("kind", ["rotation", "sequence"])
@pytest.mark.parametrize("phase", ["add", "remove"])
@pytest.mark.parametrize("read_fails", [False, True])
def test_lost_reply_reports_actual_state_without_replaying(monkeypatch, ctl_type, game, kind, phase, read_fails):
    ctl = ctl_type(ServerInfo(game=game))
    state = ["old_a", "old_b"]
    setattr(ctl, f"get_map_{kind}", Mock(return_value={"maps": [SimpleNamespace(id=x) for x in state]}))
    monkeypatch.setattr(ServerCtl, "get_maps", Mock(return_value=["new_a", "new_b"]))
    calls = []

    def add(_self, name, index):
        calls.append(("add", name))
        state.insert(index, name)
        if phase == "add" and name == "new_b":
            raise TimeoutError("response lost")

    def remove(_self, index):
        calls.append(("remove", index))
        state.pop(index)
        if phase == "remove":
            raise TimeoutError("response lost")

    def read(_self):
        if read_fails:
            raise OSError("unavailable")
        return {"maps": list(state)}

    monkeypatch.setattr(ServerCtl, f"add_map_to_{kind}_at_index", add)
    monkeypatch.setattr(ServerCtl, f"remove_map_from_{kind}_at_index", remove)
    monkeypatch.setattr(ServerCtl, f"get_map_{kind}", read)

    with pytest.raises(HLLCommandFailedError) as exc:
        getattr(ctl, f"set_map_{kind}")(["new_a", "new_b"])
    message = str(exc.value)
    assert "server may have applied the last command" in message
    assert "['old_a', 'old_b']" in message
    assert ("observed after failure: unavailable" if read_fails else f"observed after failure: {state!r}") in message
    assert calls == ([('add', 'new_a'), ('add', 'new_b')] if phase == "add" else [('add', 'new_a'), ('add', 'new_b'), ('remove', 0)])
