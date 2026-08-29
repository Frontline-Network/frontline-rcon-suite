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
