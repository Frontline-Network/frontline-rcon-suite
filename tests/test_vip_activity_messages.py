import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")

from tests.test_leadership_vote import db
from rcon import vip_activity_messages as offers
from rcon.models import AdminIncident, AdminIncidentEvent, LogLine, PlayerID, PlayerOptins, PlayersAction
from rcon.user_config.auto_broadcast import VIP_LIFECYCLE_DEFAULT_MESSAGES
from rcon.user_config.end_match_stats import EndMatchStatsUserConfig

NOW = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc)
EOS = "0002abcdef01234567890123456789ab"


def test_recipient_language_reminder_and_expiry(monkeypatch):
    monkeypatch.setenv("HLL_GAME", "hllv")
    monkeypatch.setenv("FRONTLINE_VIP_STATUS_URL", "https://fln.gg/status")
    render = lambda rule, **kwargs: offers.render_activity_message(
        rule=rule, player_id=EOS, source=kwargs.pop("source", VIP_LIFECYCLE_DEFAULT_MESSAGES[rule]), **kwargs)
    monkeypatch.setattr(offers, "preferred_language", lambda _: "fr")
    assert "téléphone" in render("unverified")
    assert "prioritaire" in render("unverified", source="Original", translations={"fr":"Première invitation"}, reminder=True)
    assert render("unverified", source="Original", translations={"fr":"Mon invitation"}).startswith("Mon invitation")
    assert "2026-11-28 12:00 UTC" in render("trial_expiring", expires_at="2026-11-28T13:00:00+01:00")
    assert render("trial_expiring", expires_at=None) == ""
    monkeypatch.setattr(offers, "preferred_language", lambda _: "pl")
    assert render("unverified").startswith("Try Vietnam VIP")
    assert render("unverified", source="individuell", translations={"de": "Hallo"}) == ""
    assert render("unverified", source="individuell", translations={"en": "Custom offer"}).startswith("Custom offer")
    assert "2026-11-28" in render("trial_expired", source="custom", translations={"en":"Your trial ended."}, expires_at=NOW)
    for game, endpoint in (("hll", "https://fln.gg/test"), ("hllv", "https://elsewhere.invalid/status")):
        monkeypatch.setenv("HLL_GAME", game)
        monkeypatch.setenv("FRONTLINE_VIP_STATUS_URL", endpoint)
        assert render("unverified", reminder=True) == ""
        assert render("unverified", translations={"en":"Our own VIP"}, reminder=True).startswith("Our own VIP")


def test_chat_optout_survives_eos_case_alias_and_old_discord_choices(db, monkeypatch):
    monkeypatch.setattr(offers, "enter_session", db)
    monkeypatch.setattr(offers, "preferred_language", lambda _: "fr")
    game = Mock()
    with db() as sess:
        for model in (PlayerID, PlayerOptins):
            model.__table__.create(sess.bind)
        sess.add(PlayerID(player_id=EOS.upper()))
    assert offers.handle_chat_vip_ads(game, {"sub_content":"!VIPADS OFF", "player_id_1": EOS})
    assert "désactivées" in game.message_player.call_args.kwargs["message"]
    with db() as sess:
        sess.add(PlayerID(player_id=EOS))
        sess.flush()
        assert offers.opted_out_player_ids(sess, {EOS, EOS.upper(), "else"}) == {EOS, EOS.upper()}
        older = datetime(2000, 1, 1, tzinfo=timezone.utc)
        assert offers.set_activity_consent(sess, EOS, True, chosen_at=older) is False
    assert offers.handle_chat_vip_ads(game, {"sub_content":"!vipads on", "player_id_1": EOS.upper()})
    with db() as sess:
        assert not offers.opted_out_player_ids(sess, {EOS})
    assert not offers.handle_chat_vip_ads(game, {"sub_content":"!vipverify not-this-command"})


def test_quiet_window_protects_stats_witness_actions_and_new_round(db, monkeypatch):
    with db() as sess:
        for model in (PlayerID, PlayerOptins, PlayersAction, LogLine):
            model.__table__.create(sess.bind)
        player = PlayerID(player_id=EOS)
        sess.add(player)
        sess.flush()
        db_id = player.id
        def marker(kind, age):
            dt = datetime.fromtimestamp((NOW-timedelta(seconds=age)).timestamp())
            sess.add(LogLine(type=kind, event_time=dt, server="3", raw=kind, game=2, content="", weapon=""))
            sess.flush()
        def allowed():
            return offers.activity_message_allowed(sess, server_number=3, player_db_id=db_id, player_id=EOS, now=NOW)
        stats = EndMatchStatsUserConfig(enabled=True, include_squads=True)
        monkeypatch.setattr(EndMatchStatsUserConfig, "load_from_db", classmethod(lambda cls, **kw: stats))
        assert not allowed()  # no recent, confirmed match end
        marker("MATCH ENDED", 65)
        assert not allowed()  # squad leaderboard may still be queued
        stats.enabled = False
        assert allowed()
        case = AdminIncident(server_number=3, reporter_id="someone", target_id="other", reason="voice",
                             created_at=NOW, updated_at=NOW)
        sess.add(case)
        sess.flush()
        event = AdminIncidentEvent(incident_id=case.id, actor="bot", event_type="report_admin",
                                   payload={"status":"voice", "voice":{"witness_id":EOS}}, created_at=NOW)
        sess.add(event)
        sess.flush()
        assert not allowed()
        event.payload = {"status":"resolved"}
        sess.flush()
        assert allowed()
        action = PlayersAction(player_id_id=db_id, action_type="MESSAGE", reason="test", by="mod", time=NOW.replace(tzinfo=None))
        sess.add(action)
        sess.flush()
        assert not allowed()
        action.time -= timedelta(minutes=4)
        sess.flush()
        assert allowed()
        offers.set_activity_consent(sess, EOS, False)
        assert not allowed()
        offers.set_activity_consent(sess, EOS, True, chosen_at=datetime.now(timezone.utc)+timedelta(seconds=1))
        marker("MATCH START", 1)
        assert not allowed()
