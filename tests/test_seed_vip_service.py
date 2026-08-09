from unittest.mock import Mock

from rcon.seed_vip import service


def test_get_server_snapshot_returns_players_and_gamestate(monkeypatch):
    players = object()
    gamestate = {"num_allied_players": 2, "num_axis_players": 3}
    monkeypatch.setattr(service, "get_online_players", Mock(return_value=players))
    monkeypatch.setattr(service, "get_gamestate", Mock(return_value=gamestate))

    assert service.get_server_snapshot(Mock()) == (players, gamestate)


def test_get_server_snapshot_tolerates_transient_rcon_failure(monkeypatch):
    monkeypatch.setattr(
        service,
        "get_online_players",
        Mock(side_effect=RuntimeError("temporary RCON failure")),
    )
    get_gamestate = Mock()
    monkeypatch.setattr(service, "get_gamestate", get_gamestate)
    warning = Mock()
    monkeypatch.setattr(service.logger, "warning", warning)

    assert service.get_server_snapshot(Mock()) is None
    get_gamestate.assert_not_called()
    warning.assert_called_once()
    assert "retrying on the next poll" in warning.call_args.args[0]


def test_get_server_snapshot_retries_incomplete_result(monkeypatch):
    monkeypatch.setattr(service, "get_online_players", Mock(return_value=None))
    monkeypatch.setattr(service, "get_gamestate", Mock(return_value={}))
    warning = Mock()
    monkeypatch.setattr(service.logger, "warning", warning)

    assert service.get_server_snapshot(Mock()) is None
    warning.assert_called_once_with(
        "HLL RCON returned an incomplete Seed VIP snapshot; retrying"
    )
