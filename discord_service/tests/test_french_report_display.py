from app.report_admin_display import case_fields
from app.discord_client import _incident_log_entry, _player_stat_fields, _reporter_context_field


def test_french_cheat_review_preserves_manual_decision_and_untrusted_text():
    fields = case_fields({"assessment": {"kind": "cheat_review", "priority": "high", "reasons": ["<player> @everyone"]}}, "fr")
    assert "décision humaine uniquement" in fields[0]["name"]
    assert "preuves supplémentaires" in fields[0]["value"]
    assert "＠everyone" in fields[0]["value"]
    assert "<player>" not in fields[0]["value"]


def test_french_teamkill_analysis_never_implies_intent_from_counts():
    fields = case_fields({"assessment": {"kind": "teamkill", "reporter_teamkills": 2}}, "fr")
    assert "Cas individuel" in fields[0]["name"]
    assert "ne prouvent pas à eux seuls une intention" in fields[0]["value"]
    assert "2" in fields[0]["value"]


def test_french_stats_and_reporter_context_keep_player_data_and_unknowns():
    context = _reporter_context_field({"reporter_name": "Example", "reporter_id": "123"}, "fr")
    assert context["name"] == "👤 Contexte du signaleur"
    assert "Example" in context["value"] and "123" in context["value"]
    fields = _player_stat_fields({"deaths": 3, "kills": 6}, "fr")
    assert "Morts" in fields[0]["value"] and "3" in fields[0]["value"]


def test_french_audit_does_not_change_original_names_or_reason():
    event = {"event_type": "action", "actor": "Mod", "payload": {"action": "kick", "arguments": {"player_name": "Example", "reason": "Custom reason"}}}
    result = _incident_log_entry(event, {}, "fr")
    assert "expulsé Example" in result and "Custom reason" in result
