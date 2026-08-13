from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


ROOT = Path(__file__).resolve().parents[1]


def test_alembic_has_one_production_compatible_head():
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))

    assert ScriptDirectory.from_config(config).get_heads() == ["70d823b91325"]


def test_django_mobile_and_autobalancer_branches_merge_before_frontline_permissions():
    mobile_migration = (
        ROOT / "rconweb/api/migrations/0024_mobile_admin_auth.py"
    ).read_text(encoding="utf-8")
    merge_migration = (
        ROOT
        / "rconweb/api/migrations/0025_merge_autobalancer_mobile_admin.py"
    ).read_text(encoding="utf-8")
    desktop_migration = (
        ROOT / "rconweb/api/migrations/0026_desktop_device_code_pairing.py"
    ).read_text(encoding="utf-8")
    frontline_permissions_migration = (
        ROOT
        / "rconweb/api/migrations/0027_restore_head_admin_mobile_permissions.py"
    ).read_text(encoding="utf-8")

    assert '("api", "0023_alter_rconuser_options")' in mobile_migration
    assert '("api", "0024_add_autobalancer_permissions")' in merge_migration
    assert '("api", "0024_mobile_admin_auth")' in merge_migration
    assert '("api", "0025_merge_autobalancer_mobile_admin")' in desktop_migration
    assert '("api", "0026_desktop_device_code_pairing")' in (
        frontline_permissions_migration
    )
