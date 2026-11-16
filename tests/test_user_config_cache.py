import os
from contextlib import contextmanager
from unittest.mock import Mock

from pydantic import Field

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.user_config import utils as user_config_utils


class ExampleUserConfig(user_config_utils.BaseUserConfig):
    enabled: bool = False
    values: list[int] = Field(default_factory=list)


def setup_function():
    user_config_utils._clear_user_config_cache()


def teardown_function():
    user_config_utils._clear_user_config_cache()


def test_load_from_db_reuses_short_lived_cached_value(monkeypatch):
    monkeypatch.setenv("HLL_DB_URL", "postgresql://example.invalid/rcon")
    calls = []

    def fake_get_user_config(key, default=None):
        calls.append(key)
        return {"enabled": True, "values": [1]}

    monkeypatch.setattr(user_config_utils, "get_user_config", fake_get_user_config)

    first = ExampleUserConfig.load_from_db()
    first.values.append(2)
    second = ExampleUserConfig.load_from_db()

    assert len(calls) == 1
    assert second.enabled is True
    assert second.values == [1]


def test_cached_value_expires_after_short_ttl(monkeypatch):
    monkeypatch.setenv("HLL_DB_URL", "postgresql://example.invalid/rcon")
    clock = [100.0]
    values = iter(
        [
            {"enabled": False, "values": [1]},
            {"enabled": True, "values": [2]},
        ]
    )
    calls = []

    monkeypatch.setattr(user_config_utils.time, "monotonic", lambda: clock[0])

    def fake_get_user_config(key, default=None):
        calls.append(key)
        return next(values)

    monkeypatch.setattr(user_config_utils, "get_user_config", fake_get_user_config)

    assert ExampleUserConfig.load_from_db().enabled is False
    clock[0] += user_config_utils.USER_CONFIG_CACHE_TTL_SECONDS - 0.1
    assert ExampleUserConfig.load_from_db().enabled is False
    clock[0] += 0.2
    assert ExampleUserConfig.load_from_db().enabled is True
    assert len(calls) == 2


def test_explicit_invalidation_refreshes_cached_value(monkeypatch):
    monkeypatch.setenv("HLL_DB_URL", "postgresql://example.invalid/rcon")
    current = {"enabled": False, "values": [1]}
    calls = []

    def fake_get_user_config(key, default=None):
        calls.append(key)
        return current.copy()

    monkeypatch.setattr(user_config_utils, "get_user_config", fake_get_user_config)

    assert ExampleUserConfig.load_from_db().enabled is False
    current["enabled"] = True
    user_config_utils._invalidate_user_config_cache(ExampleUserConfig.KEY())
    assert ExampleUserConfig.load_from_db().enabled is True
    assert len(calls) == 2


def test_set_user_config_invalidates_cached_value(monkeypatch):
    monkeypatch.setenv("HLL_DB_URL", "postgresql://example.invalid/rcon")
    record = Mock(value={"enabled": False, "values": [1]})
    session = Mock()
    session.query.return_value.filter.return_value.one_or_none.return_value = record
    calls = []

    @contextmanager
    def fake_enter_session():
        yield session

    def fake_get_user_config(key, default=None):
        calls.append(key)
        return record.value.copy()

    monkeypatch.setattr(user_config_utils, "enter_session", fake_enter_session)
    monkeypatch.setattr(user_config_utils, "get_user_config", fake_get_user_config)

    assert ExampleUserConfig.load_from_db().enabled is False
    user_config_utils.set_user_config(
        ExampleUserConfig.KEY(), {"enabled": True, "values": [2]}
    )
    assert ExampleUserConfig.load_from_db().enabled is True
    assert len(calls) == 2


def test_setting_config_does_not_log_secrets(monkeypatch, caplog):
    import logging

    @contextmanager
    def fake_session():
        yield Mock()

    monkeypatch.setattr(user_config_utils, "enter_session", fake_session)
    monkeypatch.setattr(user_config_utils, "_get_conf", lambda *_: Mock())
    with caplog.at_level(logging.DEBUG, logger=user_config_utils.__name__):
        user_config_utils.set_user_config("1_Example", {"password": "fake-secret-123"})
    assert "Setting user config for 1_Example" in caplog.text
    assert "fake-secret-123" not in caplog.text


def test_invalid_config_values_are_not_logged(monkeypatch, caplog):
    monkeypatch.setenv("HLL_DB_URL", "postgresql://example.invalid/rcon")
    monkeypatch.setattr(user_config_utils, "get_user_config", lambda *_args, **_kwargs: {"enabled": "fake-secret-123"})
    assert ExampleUserConfig.load_from_db().enabled is False
    assert "fake-secret-123" not in caplog.text
    assert "validation errors" in caplog.text


def test_validation_with_reset_never_writes(monkeypatch):
    saved = Mock()
    validate = Mock()
    monkeypatch.setattr(user_config_utils, "set_user_config", saved)
    monkeypatch.setattr(ExampleUserConfig, "save_to_db", validate)
    user_config_utils.validate_user_config(
        ExampleUserConfig, {"enabled": True}, dry_run=True, reset_to_default=True
    )
    saved.assert_not_called()
    validate.assert_called_once_with(values={"enabled": True}, dry_run=True)


def test_invalid_reset_does_not_overwrite_existing_config(monkeypatch):
    import pytest
    saved = Mock()
    monkeypatch.setattr(user_config_utils, "set_user_config", saved)
    monkeypatch.setattr(ExampleUserConfig, "save_to_db", Mock(side_effect=ValueError("invalid")))
    with pytest.raises(ValueError, match="invalid"):
        user_config_utils.validate_user_config(
            ExampleUserConfig, {"enabled": "invalid"}, dry_run=False, reset_to_default=True
        )
    saved.assert_not_called()


def test_valid_reset_checks_input_before_writing(monkeypatch):
    events = []
    monkeypatch.setattr(user_config_utils, "set_user_config", lambda *_: events.append("reset"))
    monkeypatch.setattr(
        ExampleUserConfig, "save_to_db",
        lambda values, dry_run: events.append("validate" if dry_run else "save"),
    )
    user_config_utils.validate_user_config(
        ExampleUserConfig, {"enabled": True}, dry_run=False, reset_to_default=True
    )
    assert events == ["validate", "reset", "save"]


def test_config_database_error_is_not_treated_as_missing(monkeypatch):
    import pytest
    from sqlalchemy.exc import SQLAlchemyError

    session = Mock()
    session.query.return_value.filter.return_value.one_or_none.side_effect = SQLAlchemyError("offline")
    with pytest.raises(SQLAlchemyError, match="offline"):
        user_config_utils._get_conf(session, "1_Example")
    session.rollback.assert_called_once()


def test_inflight_old_read_does_not_repopulate_invalidated_cache(monkeypatch):
    import threading
    started, resume = threading.Event(), threading.Event()
    current = {"value": "old"}
    def read(_key, default=None):
        snapshot = current.copy()
        if snapshot["value"] == "old":
            started.set()
            assert resume.wait(5)
        return snapshot
    monkeypatch.setattr(user_config_utils, "get_user_config", read)
    worker = threading.Thread(target=lambda: user_config_utils._get_cached_user_config("test"))
    worker.start()
    assert started.wait(5)
    current["value"] = "new"
    user_config_utils._invalidate_user_config_cache("test")
    resume.set()
    worker.join(5)
    assert not worker.is_alive()
    assert user_config_utils._get_cached_user_config("test") == {"value": "new"}
