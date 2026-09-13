import ast
from pathlib import Path
from unittest import TestCase


MIGRATIONS = Path(__file__).resolve().parents[1] / "rconweb/api/migrations"


def migration_assignments(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    migration = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Migration"
    )
    return {
        target.id: node.value
        for node in migration.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
    }


class DjangoMigrationGraphTests(TestCase):
    def test_api_has_one_migration_leaf(self):
        # Inspect static API dependencies without importing runtime services or
        # connecting to a database. CI also applies the full graph to PostgreSQL.
        paths = list(MIGRATIONS.glob("[0-9]*.py"))
        names = {path.stem for path in paths}
        dependencies = set()
        for path in paths:
            for node in migration_assignments(path)["dependencies"].elts:
                if isinstance(node, ast.Tuple):
                    app, name = ast.literal_eval(node)
                    if app == "api":
                        dependencies.add(name)
        self.assertFalse(dependencies - names, "Missing API migration dependency")
        self.assertEqual(names - dependencies, {"0037_merge_eventador_live_view"})

    def test_merge_preserves_both_existing_migrations_without_data_operations(self):
        values = migration_assignments(
            MIGRATIONS / "0037_merge_eventador_live_view.py"
        )
        self.assertEqual(
            set(ast.literal_eval(values["dependencies"])),
            {
                ("api", "0036_eventador_control_steps"),
                ("api", "0036_user_live_view_preference"),
            },
        )
        self.assertEqual(ast.literal_eval(values["operations"]), [])
