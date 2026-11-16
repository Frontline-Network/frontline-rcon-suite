from unittest.mock import Mock

from rcon import api_commands
from rcon.api_commands import RconAPI


def test_saved_config_is_audited_but_validation_is_not(monkeypatch):
    model = Mock()
    model.load_from_db.side_effect = [{"enabled": False}, {"enabled": True}, {"enabled": False}]
    validate = Mock(return_value=True)
    audit = Mock()
    monkeypatch.setattr(api_commands, "validate_user_config", validate)
    monkeypatch.setattr(api_commands, "audit_user_config_differences", audit)
    assert RconAPI._validate_user_config("set_config", "admin", model, {"enabled": True}, dry_run=False) is True
    assert audit.call_args.kwargs["new_model"] == {"enabled": True}
    assert RconAPI._validate_user_config("validate_config", "admin", model, {"enabled": True}, dry_run=True) is True
    assert audit.call_count == 1


def test_audit_failure_does_not_report_saved_config_as_failed(monkeypatch):
    model = Mock()
    model.load_from_db.return_value = {"enabled": True}
    monkeypatch.setattr(api_commands, "validate_user_config", Mock(return_value=True))
    monkeypatch.setattr(api_commands, "audit_user_config_differences", Mock(side_effect=RuntimeError("audit unavailable")))
    assert RconAPI._validate_user_config("set_config", "admin", model, {"enabled": True}, dry_run=False) is True
