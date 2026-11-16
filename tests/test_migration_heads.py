from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

ROOT = Path(__file__).resolve().parents[1]


def test_alembic_has_one_production_compatible_head():
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))

    scripts = ScriptDirectory.from_config(config)
    assert scripts.get_heads() == ["b3530a1b2c3d"]
    assert scripts.get_revision("b3530a1b2c3d").down_revision == "a3170a1b2c3d"
    assert scripts.get_revision("a3170a1b2c3d").down_revision == "f3400a1b2c3d"
    assert scripts.get_revision("f3400a1b2c3d").down_revision == "f3520a1b2c3d"
    assert scripts.get_revision("f3520a1b2c3d").down_revision == "e3150a1b2c3d"
    assert scripts.get_revision("e3150a1b2c3d").down_revision == "d3650a1b2c3d"
    assert scripts.get_revision("d3650a1b2c3d").down_revision == "c9d4e6a81111"
    assert set(scripts.get_revision("c9d4e6a81111").down_revision) == {
        "c8e2a4f61009", "f4b9c2d6e310"
    }
    assert scripts.get_revision("f4b9c2d6e310").down_revision == "e3a8b1c5d209"
    assert scripts.get_revision("e3a8b1c5d209").down_revision == "d2f7a4c9b8e1"
    assert scripts.get_revision("d2f7a4c9b8e1").down_revision == "b7e9d5026a31"


def test_audit_time_index_is_created_concurrently():
    migration = (
        ROOT / "alembic/versions/b8e3a1f4c6d2_index_audit_log_creation_time.py"
    ).read_text(encoding="utf-8")

    assert 'down_revision = "a4c7e9f2b681"' in migration
    assert '"ix_audit_log_creation_time"' in migration
    assert "postgresql_concurrently=True" in migration
    assert "autocommit_block" in migration


def test_log_server_time_index_is_created_concurrently():
    migration = (
        ROOT
        / "alembic/versions/c9e1f4a7b2d6_index_log_lines_by_server_and_time.py"
    ).read_text(encoding="utf-8")

    assert 'down_revision = "8d0f4a2c9b71"' in migration
    assert '"ix_log_lines_server_event_time"' in migration
    assert '["server", "event_time"]' in migration
    assert "postgresql_concurrently=True" in migration
    assert "autocommit_block" in migration


def test_django_mobile_and_autobalancer_branches_merge_before_frontline_permissions():
    mobile_migration = (
        ROOT / "rconweb/api/migrations/0024_mobile_admin_auth.py"
    ).read_text(encoding="utf-8")
    merge_migration = (
        ROOT / "rconweb/api/migrations/0025_merge_autobalancer_mobile_admin.py"
    ).read_text(encoding="utf-8")
    desktop_migration = (
        ROOT / "rconweb/api/migrations/0026_desktop_device_code_pairing.py"
    ).read_text(encoding="utf-8")
    frontline_permissions_migration = (
        ROOT / "rconweb/api/migrations/0027_restore_head_admin_mobile_permissions.py"
    ).read_text(encoding="utf-8")

    assert '("api", "0023_alter_rconuser_options")' in mobile_migration
    assert '("api", "0024_add_autobalancer_permissions")' in merge_migration
    assert '("api", "0024_mobile_admin_auth")' in merge_migration
    assert '("api", "0025_merge_autobalancer_mobile_admin")' in desktop_migration
    assert '("api", "0026_desktop_device_code_pairing")' in (
        frontline_permissions_migration
    )
