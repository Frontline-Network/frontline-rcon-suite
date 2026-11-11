"""The documented `alembic upgrade head` must remain unambiguous."""

from pathlib import Path

from alembic.script import ScriptDirectory


def test_release_has_one_migration_head_covering_population_and_rewards():
    scripts = ScriptDirectory(str(Path(__file__).resolve().parents[1] / "alembic"))
    assert len(scripts.get_heads()) == 1
    revisions = {entry.revision for entry in scripts.walk_revisions()}
    assert {"c8e2a4f61009", "f4b9c2d6e310"}.issubset(revisions)
