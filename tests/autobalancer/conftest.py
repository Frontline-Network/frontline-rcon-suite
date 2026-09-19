import pytest

from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig


@pytest.fixture(autouse=True)
def isolated_seeding_configuration(monkeypatch):
    """Never consult a real database in the isolated autobalancer suite."""
    monkeypatch.setattr(
        AutoModSeedingUserConfig,
        "load_from_db",
        lambda: AutoModSeedingUserConfig(enabled=False),
    )
