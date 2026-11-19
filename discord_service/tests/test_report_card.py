import pytest

from discord_service.app.contracts import IncidentEventEnvelope
from discord_service.app.discord_client import render_message
from discord_service.tests.test_service import _event


def card(**changes):
    event = _event()
    event["incident"].update(discord_language="en")
    event["incident"].update(changes)
    return render_message(IncidentEventEnvelope.model_validate(event), None)["embeds"][0]


@pytest.mark.parametrize(("phase", "expected"), [
    ("notice_pending", "reminder queued"), ("notice_sent", "confirmed the reminder"),
    ("awaiting_answer", "Waiting for a reply")
])
def test_voice_from_current_incident_event(phase, expected):
    voice = {"phase": phase, "channel": "command"}
    if phase != "notice_pending":
        voice["notice_sent_at"] = 1100
    if phase == "awaiting_answer":
        voice["question_at"] = 1160
    result = card(report_admin={"rule": "communication", "status": "voice"},
                  events=[{"event_type": "report_admin", "payload": {"voice": voice}}])
    description = result["description"]
    assert expected in description.splitlines()[0]
    assert "No admin action needed now" in description.splitlines()[0]
    assert "Manual review" not in str(result)
    assert ("<t:1100:T>" in description) == (phase != "notice_pending")
    assert ("<t:1160:T>" in description) == (phase == "awaiting_answer")


@pytest.mark.parametrize(("incident", "expected"), [
    ({"status": "resolved", "report_admin": {"status": "voice"}}, "Closed"),
    ({"status": "dismissed"}, "Report dismissed"),
    ({"status": "claimed", "assigned_to": "discord:23:Lou"}, "Being handled by Lou"),
    ({"source": "ai_chat"}, "Chat message flagged for review"),
    ({"source": "ai_player_name"}, "Player name flagged for review"),
    ({"leadership_vote": {"status": "active"}}, "No admin action needed now"),
    ({"leadership_vote": {"status": "rejected"}}, "Admin review needed"),
    ({"report_admin": {"status": "unknown"}}, "Action outcome unconfirmed"),
    ({"report_admin": {"status": "dry_run"}}, "Dry run completed without a kick"),
    ({"report_admin": {"status": "manual", "voice": {"message_key": "expired"}}}, "Reply deadline expired"),
    ({"report_admin": {"status": "queued", "voice": {"phase": "kick_ready"}}}, "checking kick eligibility"),
    ({"status": "resolved", "report_admin": {"status": "resolved", "voice": {"phase": "resolved", "answer": "working"}}}, "Communication restored according to the reply"),
])
def test_report_summary(incident, expected):
    assert expected in card(**incident)["description"]


@pytest.mark.parametrize(("language", "outcome"), [("de", "Adminprüfung nötig"), ("fr", "Examen par un admin requis")])
def test_manual_attention_in_channel_language(language, outcome):
    assert outcome in card(discord_language=language)["description"].splitlines()[0]
