"""Persist uncertain automated actions and their review history.

Revision ID: a3170a1b2c3d
Revises: f3400a1b2c3d
"""
from alembic import op
import sqlalchemy as sa

revision = "a3170a1b2c3d"
down_revision = "f3400a1b2c3d"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("automod_action_guard") or inspector.has_table("automod_action_guard_history"):
        # A staged pilot must be checked, rather than silently accepting an
        # incomplete or incompatible table from another installation.
        if not inspector.has_table("automod_action_guard") or not inspector.has_table("automod_action_guard_history"):
            raise RuntimeError("Incomplete staged automod guard schema")
        expected = {
            "automod_action_guard": ({"server_number", "player_id", "rule", "action", "token", "state", "updated_at", "reviewed_by", "review_reason"},
                                      {"server_number", "player_id", "rule", "action"},
                                      {"ix_automod_action_guard_token", "ix_automod_action_guard_state"},
                                      {"ck_automod_guard_server", "ck_automod_guard_action", "ck_automod_guard_state"}),
            "automod_action_guard_history": ({"id", "server_number", "player_id", "token", "event", "rules_json", "action", "created_at", "actor", "reason"},
                                              {"id"}, {"ix_automod_action_guard_history_server_number", "ix_automod_action_guard_history_token"},
                                              {"ck_automod_guard_history_server", "ck_automod_guard_history_event"}),
        }
        for name, (columns, primary, indexes, checks) in expected.items():
            column_info = {item["name"]: item for item in inspector.get_columns(name)}
            if (set(column_info) != columns
                    or set(inspector.get_pk_constraint(name)["constrained_columns"]) != primary
                    or not indexes.issubset({item["name"] for item in inspector.get_indexes(name)})
                    or not checks.issubset({item["name"] for item in inspector.get_check_constraints(name)})):
                raise RuntimeError(f"Unexpected staged automod guard schema: {name}")
            nullable = {"reviewed_by", "review_reason"} if name == "automod_action_guard" else {"rules_json", "action", "actor", "reason"}
            lengths = ({"player_id": 100, "rule": 150, "action": 20, "token": 32, "state": 20, "reviewed_by": 150}
                       if name == "automod_action_guard" else
                       {"id": 32, "player_id": 100, "token": 32, "event": 20, "action": 20, "actor": 150})
            for key, column in column_info.items():
                if bool(column["nullable"]) != (key in nullable):
                    raise RuntimeError(f"Unexpected nullability: {name}.{key}")
                if key in lengths and (not isinstance(column["type"], sa.String) or column["type"].length != lengths[key]):
                    raise RuntimeError(f"Unexpected string type: {name}.{key}")
                if key in {"updated_at", "created_at"} and (not isinstance(column["type"], sa.DateTime) or not column["type"].timezone):
                    raise RuntimeError(f"Unexpected timestamp type: {name}.{key}")
                if key == "server_number" and not isinstance(column["type"], sa.Integer):
                    raise RuntimeError(f"Unexpected server type: {name}.{key}")
        return
    op.create_table(
        "automod_action_guard",
        sa.Column("server_number", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.String(100), primary_key=True),
        sa.Column("rule", sa.String(150), primary_key=True),
        sa.Column("action", sa.String(20), primary_key=True),
        sa.Column("token", sa.String(32), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(150), nullable=True),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_automod_guard_server"),
        sa.CheckConstraint("action IN ('message', 'punish', 'kick')", name="ck_automod_guard_action"),
        sa.CheckConstraint("state IN ('pending', 'confirmed', 'rejected', 'reviewed')", name="ck_automod_guard_state"),
    )
    op.create_index("ix_automod_action_guard_token", "automod_action_guard", ["token"])
    op.create_index("ix_automod_action_guard_state", "automod_action_guard", ["state"])
    op.create_table(
        "automod_action_guard_history",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.String(100), nullable=False),
        sa.Column("token", sa.String(32), nullable=False),
        sa.Column("event", sa.String(20), nullable=False),
        sa.Column("rules_json", sa.Text(), nullable=True),
        sa.Column("action", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(150), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_automod_guard_history_server"),
        sa.CheckConstraint("event IN ('reserved', 'confirmed', 'rejected', 'reviewed')", name="ck_automod_guard_history_event"),
    )
    op.create_index("ix_automod_action_guard_history_server_number", "automod_action_guard_history", ["server_number"])
    op.create_index("ix_automod_action_guard_history_token", "automod_action_guard_history", ["token"])


def downgrade():
    op.drop_index("ix_automod_action_guard_history_token", table_name="automod_action_guard_history")
    op.drop_index("ix_automod_action_guard_history_server_number", table_name="automod_action_guard_history")
    op.drop_table("automod_action_guard_history")
    op.drop_index("ix_automod_action_guard_state", table_name="automod_action_guard")
    op.drop_index("ix_automod_action_guard_token", table_name="automod_action_guard")
    op.drop_table("automod_action_guard")
