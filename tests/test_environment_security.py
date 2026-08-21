import pytest

from rconweb.rconweb.environment import load_secret, normalize_cors_origin, read_bool_env


def test_read_bool_env_accepts_explicit_values(monkeypatch):
    monkeypatch.setenv("FLAG", "false")
    assert read_bool_env("FLAG") is False
    monkeypatch.setenv("FLAG", "yes")
    assert read_bool_env("FLAG") is True


def test_read_bool_env_rejects_ambiguous_values(monkeypatch):
    monkeypatch.setenv("FLAG", "definitely")
    with pytest.raises(ValueError, match="FLAG must be one of"):
        read_bool_env("FLAG")


def test_load_secret_requires_configured_value_outside_test_mode(monkeypatch):
    monkeypatch.delenv("RCONWEB_API_SECRET", raising=False)
    with pytest.raises(ValueError, match="RCONWEB_API_SECRET must be set"):
        load_secret(test_mode=False)
    assert load_secret(test_mode=True) == "test-only-rconweb-secret-not-for-production"


def test_load_secret_accepts_legacy_short_values_with_a_warning(monkeypatch, caplog):
    monkeypatch.setenv("RCONWEB_API_SECRET", "too-short")
    assert load_secret(test_mode=False) == "too-short"
    assert "shorter than 32 characters" in caplog.text
    assert "too-short" not in caplog.text


def test_normalize_cors_origin_requires_https_in_production():
    assert (
        normalize_cors_origin("https://webapp.fln.gg/", allow_insecure=False)
        == "https://webapp.fln.gg"
    )
    with pytest.raises(ValueError, match="may only contain HTTPS"):
        normalize_cors_origin("http://webapp.fln.gg", allow_insecure=False)
    with pytest.raises(ValueError, match="without a path"):
        normalize_cors_origin("https://webapp.fln.gg/api", allow_insecure=False)
