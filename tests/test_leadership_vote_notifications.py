"""Information delivery must not masquerade as a manual moderation action."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from tests.test_leadership_vote import (
    activate,
    cast,
    confirm,
    context,
    db,
    deliver,
    elapse,
    observe_for,
    report,
    roster,
    vote,
)
from rcon import campaign_delivery, rcon as rcon_module
from rcon.commands import ServerCtl
from rcon.leadership_vote import storage
from rcon.types import PlayerActionState


@pytest.fixture(params=[rcon_module.HLLRcon, rcon_module.HLLVRcon])
def controller(request, monkeypatch):
    # Exercise the real shared message wrapper without a game connection.
    ctl = object.__new__(request.param)
    sent = Mock(return_value=True)
    audit = Mock()
    monkeypatch.setattr(ServerCtl, "message_player", sent)
    monkeypatch.setattr(rcon_module, "safe_save_player_action", audit)
    monkeypatch.setattr(
        rcon_module.RconServerSettingsUserConfig,
        "load_from_db",
        lambda: SimpleNamespace(message_enhancements=SimpleNamespace(enabled=False)),
    )
    return SimpleNamespace(api=ctl, sent=sent, audit=audit)


def run_campaign_once(monkeypatch, ctl):
    """Use the actual campaign send call, replacing only its I/O and endless loop."""
    campaign = SimpleNamespace(pause_during_seeding=False)
    config = SimpleNamespace(enabled=True, vip_lifecycle=SimpleNamespace(enabled=False))
    monkeypatch.setattr(rcon_module, "get_rcon", lambda: ctl)
    monkeypatch.setattr(campaign_delivery, "get_server_number", lambda: 1)
    monkeypatch.setattr(campaign_delivery, "_recover_interrupted_deliveries", Mock())
    monkeypatch.setattr(campaign_delivery, "expire_old_deliveries", Mock())
    monkeypatch.setattr(
        campaign_delivery.AutoBroadcastUserConfig, "load_from_db", lambda: config
    )
    monkeypatch.setattr(
        campaign_delivery, "_all_direct_campaigns", lambda _: [campaign]
    )
    monkeypatch.setattr(campaign_delivery, "_direct_campaigns", lambda _: [campaign])
    monkeypatch.setattr(campaign_delivery, "_online_players", lambda _: {"target": {}})
    monkeypatch.setattr(campaign_delivery, "_active_sessions", lambda *_: {})
    monkeypatch.setattr(campaign_delivery, "enqueue_eligible_deliveries", Mock())
    monkeypatch.setattr(
        campaign_delivery,
        "claim_next_delivery",
        lambda **_: {
            "id": 1,
            "campaign_id": "info",
            "campaign_title": "Microphone reminder",
            "player_id": "target",
            "player_name": "Person-target",
            "message": "Please use leadership voice chat.",
        },
    )
    monkeypatch.setattr(
        campaign_delivery, "format_message", lambda _, message, **kw: message
    )
    finished = Mock()
    monkeypatch.setattr(campaign_delivery, "finish_delivery", finished)
    monkeypatch.setattr(
        campaign_delivery.time, "sleep", Mock(side_effect=StopIteration)
    )
    with pytest.raises(StopIteration):
        campaign_delivery.run()
    return finished


@pytest.mark.parametrize("commander", [False, True], ids=["squadleader", "commander"])
def test_separate_language_invitations_use_real_hll_and_hllv_message_wrapper(
    db, controller, commander
):
    players = roster(commander=commander)
    observe_for(db, players)
    incident = report(players, "!admin commander" if commander else "!admin able")
    vid = confirm(db, players, incident, deliver_invitations=False)
    storage.advance(1, context(players))
    deliver(db, players, controller.api)
    calls = controller.sent.call_args_list
    assert len(calls) == 12
    for i in range(6):
        bodies = [c.args[1] for c in calls if c.args[0] == f"v{i}"]
        assert len(bodies) == 2
        assert "FÜHRUNGSABSTIMMUNG" in bodies[0]
        assert "LEADERSHIP VOTE" in bodies[1]
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "active"
    assert vote(db, vid)["required"] == 4


@pytest.mark.parametrize("commander", [False, True], ids=["squadleader", "commander"])
@pytest.mark.parametrize("phase", ["confirming", "inviting", "active", "executing"])
def test_campaign_preserves_vote_and_message_audit(
    db, monkeypatch, controller, commander, phase
):
    if phase in {"active", "executing"}:
        vid, players = activate(db, commander=commander, mode="active")
        if phase == "executing":
            for i in range(4):
                assert cast(db, players, f"v{i}")
            elapse(db, players, 120)
            assert len(storage.advance(1, context(players))) == 1
            assert storage.begin_send(1, vid, context(players))
    else:
        players = roster(commander=commander)
        observe_for(db, players)
        incident = report(
            players, text="!admin commander" if commander else "!admin able"
        )
        vid = incident["leadership_vote"]["id"]
        if phase == "inviting":
            confirm(db, players, incident)
    before = vote(db, vid)
    assert before["status"] == phase

    finished = run_campaign_once(monkeypatch, controller.api)

    assert vote(db, vid) == before
    controller.sent.assert_called_once_with(
        "target", "Please use leadership voice chat."
    )
    controller.audit.assert_called_once_with(
        player_id="target",
        player_name="Person-target",
        action_type=PlayerActionState.MESSAGE,
        reason="Please use leadership voice chat.",
        by="Campaign: Microphone reminder",
    )
    assert finished.call_args.kwargs["success"] is True


@pytest.mark.parametrize("actor", ["admin", "Campaign: is only an actor label"])
def test_saved_admin_message_still_cancels_vote(db, controller, actor):
    vid, _ = activate(db)
    assert controller.api.message_player(
        "target", "Admin warning", by=actor, save_message=True
    )
    assert vote(db, vid)["status"] == "cancelled"
    assert vote(db, vid)["result"] == "Manuelle Maßnahme / Manual action"
    controller.sent.assert_called_once_with("target", "Admin warning")
    controller.audit.assert_called_once()


def test_saved_admin_message_cannot_race_a_started_kick(db, controller):
    from tests.test_leadership_vote import ready_to_kick
    from rcon.admin_incidents import IncidentConflict

    vid, players, _ = ready_to_kick(db)
    assert storage.begin_send(1, vid, context(players))
    with pytest.raises(IncidentConflict, match="send already started"):
        controller.api.message_player(
            "target", "Admin warning", by="admin", save_message=True
        )
    controller.sent.assert_not_called()
    controller.audit.assert_not_called()


@pytest.mark.parametrize("response", [False, TimeoutError("uncertain delivery")])
def test_failed_information_send_does_not_cancel_vote_or_audit_success(
    db, monkeypatch, controller, response
):
    vid, _ = activate(db)
    if isinstance(response, Exception):
        controller.sent.side_effect = response
    else:
        controller.sent.return_value = response

    finished = run_campaign_once(monkeypatch, controller.api)

    assert vote(db, vid)["status"] == "active"
    controller.audit.assert_not_called()
    assert finished.call_args.kwargs["success"] is False


def test_information_delivery_keeps_message_enhancements(db, monkeypatch, controller):
    vid, _ = activate(db)
    monkeypatch.setattr(
        rcon_module.RconServerSettingsUserConfig,
        "load_from_db",
        lambda: SimpleNamespace(
            message_enhancements=SimpleNamespace(
                enabled=True, message_header="Server", message_footer="Rules"
            )
        ),
    )
    assert controller.api.message_player_info(
        "target", "VIP information", "VIP lifecycle: trial_active"
    )
    controller.sent.assert_called_once_with(
        "target", "Server\n\nVIP information\n\nRules"
    )
    assert (
        controller.audit.call_args.kwargs["reason"]
        == "Server\n\nVIP information\n\nRules"
    )
    assert vote(db, vid)["status"] == "active"
