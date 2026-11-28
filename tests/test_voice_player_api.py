"""Player callbacks operate on the caller's cases and verified game identity only."""

import re
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from tests.test_report_admin_api import db, setup
from tests.test_voice_reports import pilot, snapshot
from tests.test_report_reason import complete, decision
from tests.test_report_admin import service, transport
from api import voice_player_api as api
from rcon import voice_language as lang
from rcon.models import AdminIncident
from rcon.user_config.report_admin import ReportAdminUserConfig as Config
from rcon.voice_player_store import VoiceDraft, VoiceLinkChallenge, VoicePlayerDelivery


@pytest.fixture
def panel(pilot, monkeypatch):
    setup, advance = pilot
    database, players, ctx = setup
    game = transport()
    monkeypatch.setattr(api, "enter_session", database)
    monkeypatch.setattr(api, "get_rcon_api", lambda: game)
    monkeypatch.setattr(api, "read_context", lambda _: ctx)
    with database() as s:
        for t in (VoiceLinkChallenge, VoiceDraft):
            t.__table__.create(s.bind)
    service.configure(1, Config(enabled=True, mode="dry_run", reason_mode="ai"))
    return setup, advance, game


def test_pick_online_identity_with_duplicate_names_and_revalidate_departure(panel):
    setup, _, _ = panel
    database, players, _ = setup
    players[1]["name"] = players[0]["name"]
    choices = api._handle(1, "1234", "300", "roster", {})["players"]
    target_ref = api._roster_ref(1, "1234", players[1])
    assert target_ref in {p["ref"] for p in choices} and "player_id" not in choices[0]
    assert api._roster_ref(1, "4567", players[1]) != target_ref
    args = {
        "message": "Squad leader not answering in squad chat",
        "target_ref": target_ref,
    }
    result = api._handle(1, "1234", "301", "report", args)
    with database() as s:
        assert (
            s.get(AdminIncident, result["incident_id"]).target_id
            == players[1]["player_id"]
        )
    players[1]["online"] = False
    stale = api._handle(
        1, "1234", "302", "report", {**args, "target": players[0]["name"]}
    )
    assert stale["actions"][0]["operation"] == "clarify"
    with database() as s:
        assert not s.get(AdminIncident, stale["incident_id"])


def test_console_report_polish_receipt_and_english_default_target(panel):
    setup, advance, game = panel
    database, players, ctx = setup
    name = players[0]["name"]
    text = "Nasz dowódca oddziału od kilku minut nie odpowiada nam przez radio."
    submission = {"message": text, "target": name}
    result = api._handle(1, "1234", "321", "report", submission)
    iid = result["incident_id"]
    assert result["content"].startswith("Zgłoszenie")
    assert api._handle(1, "1234", "321", "report", submission)["incident_id"] == iid
    with database() as s:
        assert s.get(AdminIncident, iid).reporter_id is None
        assert lang.preferred_language(s, game_id=players[0]["player_id"]) == "en"
        assert api._list(s, 1, "9876", "en")["content"] == "No reports yet."
    complete(setup, iid, decision(target=name, excerpt=text))
    service.tick(game, 1)
    service.tick(game, 1)
    assert snapshot(database, iid)["voice"]["phase"] == "notice_sent"
    sent = game.message_player.call_args_list[0].args
    assert sent[0] == players[0]["player_id"]
    assert sent[1] == "Your squad is trying to reach you. Please respond in squad voice."
    with database() as s:
        delivery = s.scalar(
            select(VoicePlayerDelivery).where(VoicePlayerDelivery.incident_id == iid)
        )
        assert delivery.discord_id == "1234" and delivery.payload["locale"] == "pl"
        listing = api._list(s, 1, "1234", "en")["content"]
        assert "Wysłaliśmy" in listing
        assert iid[:8] not in listing and re.search(r"<t:\d+:t>", listing)
    game.kick.assert_not_called()


def test_clarification_is_private_and_idempotent(panel):
    setup, _, _ = panel
    draft = api._handle(
        1,
        "101",
        "404",
        "report",
        {"message": "The officer won't answer in squad voice.", "target": "unknown"},
    )
    did = draft["incident_id"]
    assert draft["actions"][0]["operation"] == "clarify"
    with pytest.raises(ValueError):
        api._handle(
            1,
            "102",
            "405",
            "clarify",
            {"incident_id": did, "target": setup[1][0]["name"]},
        )
    args = {"incident_id": did, "target": setup[1][0]["name"]}
    case = api._handle(1, "101", "406", "clarify", args)
    assert case["incident_id"] != did and case == api._handle(
        1, "101", "407", "clarify", args
    )


def test_private_code_joins_language_only_after_success(panel):
    setup, _, game = panel
    database, players, _ = setup
    name, pid = players[0]["name"], players[0]["player_id"]
    api._handle(1, "100", "801", "language", {"language": "fr"})
    api._handle(1, "100", "802", "link", {"player": name})
    code = re.search(r"\b\d{8}\b", game.message_player.call_args.args[1]).group()
    assert game.message_player.call_args.kwargs["save_message"] is False
    api._handle(1, "101", "803", "verify", {"code": code})
    with database() as s:
        assert not lang.linked_discord_id(s, pid)
    api._handle(1, "100", "804", "verify", {"code": code})
    with database() as s:
        assert lang.linked_discord_id(s, pid) == "100"
        assert lang.preferred_language(s, game_id=pid) == "fr"


def test_callback_guild_and_installation_must_match(monkeypatch):
    from django.test import RequestFactory

    monkeypatch.setattr(
        api,
        "_authorized_integration",
        lambda *args: (SimpleNamespace(installation_id="abc", guild_id="987"), None),
    )
    handler = Mock()
    monkeypatch.setattr(api, "_handle", handler)
    for guild, installation in (("wrong", "abc"), ("987", "wrong")):
        req = RequestFactory().post(
            "/api/discord/v1/player-reports",
            {"guild_id": guild, "installation_id": installation},
            content_type="application/json",
        )
        assert api.player_reports(req).status_code == 404
    handler.assert_not_called()


def test_linked_account_cannot_read_moderator_created_case(panel):
    setup, _, _ = panel
    database, players, _ = setup
    pid = players[0]["player_id"]
    with database() as sess:
        lang.link_verified(sess, game_id=pid, discord_id="100")
    incident, _ = api.create_incident(
        server_number=1,
        source="manual",
        reason="private moderator case",
        actor="moderator",
        reporter_id=pid,
        reporter_context={"voice_discord_id": "100"},
    )
    with database() as sess:
        listing = api._list(sess, 1, "100", "en")
        assert incident["id"][:8] not in listing["content"]
        assert listing["content"] == "No reports yet."


def test_worker_retries_same_private_edit_without_resending_a_dm(panel, monkeypatch):
    from api import voice_player_worker as worker
    from datetime import datetime, timezone

    database, players, _ = panel[0]
    case, _ = api.create_incident(
        server_number=1, source="manual", reason="test", actor="moderator"
    )
    with database() as sess:
        sess.add(
            VoicePlayerDelivery(
                incident_id=case["id"],
                discord_id="100",
                kind="final",
                attempts=0,
                done=False,
                due=datetime(2020, 1, 1, tzinfo=timezone.utc),
                payload={
                    "locale": "pl",
                    "key": "closed",
                    "target": "",
                    "question": False,
                    "send_dm": True,
                    "server_number": 1,
                },
            )
        )
    monkeypatch.setattr(worker, "enter_session", database)
    monkeypatch.setattr(worker, "decrypt_capability", lambda _: "mock")
    config = SimpleNamespace(
        installation_id="test",
        outbound_capability_ciphertext="mock",
        service_url="https://discord.invalid",
    )
    monkeypatch.setattr(
        worker.DiscordReportIntegration.objects,
        "filter",
        lambda **kw: SimpleNamespace(first=lambda: config),
    )
    http = Mock()
    http.post.return_value.json.side_effect = [
        {"accepted": True, "retry_ephemeral": True},
        {"accepted": True},
    ]
    assert worker.deliver_one(http)
    with database() as sess:
        row = sess.scalar(select(VoicePlayerDelivery))
        assert not row.done
        row.due = datetime(2020, 1, 1, tzinfo=timezone.utc)
    assert worker.deliver_one(http)
    assert not worker.deliver_one(http)
    assert http.post.call_args_list[0].kwargs == http.post.call_args_list[1].kwargs
