"""Persist map-vote reminder batches and recipient reservations.

Revision ID: d3330a1b2c3d
Revises: c3230a1b2c3d
"""
from alembic import op
import sqlalchemy as sa

revision = "d3330a1b2c3d"
down_revision = "c3230a1b2c3d"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    present = [inspector.has_table(name) for name in ("votemap_reminder_clock", "votemap_reminder_batch", "votemap_reminder_delivery")]
    if any(present):
        if not all(present):
            raise RuntimeError("Votemap reminder staging is incomplete")
        expected = {
            "votemap_reminder_clock": {
                "columns": {"server_number": (sa.Integer, None, False), "completed_at": (sa.Float, None, False), "outcome": (sa.String, 16, False)},
                "primary": {"server_number"}, "checks": {"ck_votemap_clock_server", "ck_votemap_clock_outcome"},
            },
            "votemap_reminder_batch": {
                "columns": {"server_number": (sa.Integer, None, False), "scope": (sa.String, 100, False),
                            "batch_id": (sa.String, 64, False), "signature": (sa.String, 64, False),
                            "message": (sa.Text, None, False), "status": (sa.String, 16, False),
                            "created_at": (sa.Float, None, False), "completed_at": (sa.Float, None, True)},
                "primary": {"server_number", "scope"}, "checks": {"ck_votemap_batch_server", "ck_votemap_batch_status"},
            },
            "votemap_reminder_delivery": {
                "columns": {"server_number": (sa.Integer, None, False), "batch_id": (sa.String, 64, False),
                            "player_id": (sa.String, 100, False), "token": (sa.String, 32, False),
                            "status": (sa.String, 16, False), "attempts": (sa.Integer, None, False),
                            "updated_at": (sa.Float, None, False), "retry_at": (sa.Float, None, False)},
                "primary": {"server_number", "batch_id", "player_id"},
                "checks": {"ck_votemap_notice_server", "ck_votemap_notice_status", "ck_votemap_notice_attempts"},
            },
        }
        for name, specification in expected.items():
            columns = {column["name"]: column for column in inspector.get_columns(name)}
            if set(columns) != set(specification["columns"]):
                raise RuntimeError(f"Unexpected staged Votemap reminder schema: {name} columns")
            for key, (kind, length, nullable) in specification["columns"].items():
                column = columns[key]
                if (not isinstance(column["type"], kind) or column["nullable"] != nullable
                        or (length is not None and column["type"].length != length)):
                    raise RuntimeError(f"Unexpected staged Votemap reminder schema: {name}.{key}")
            primary = set(inspector.get_pk_constraint(name)["constrained_columns"])
            checks = {constraint["name"] for constraint in inspector.get_check_constraints(name)}
            if primary != specification["primary"] or not specification["checks"].issubset(checks):
                raise RuntimeError(f"Unexpected staged Votemap reminder constraints: {name}")
        unique = inspector.get_unique_constraints("votemap_reminder_batch")
        if not any(item["name"] == "uq_votemap_batch_server_id"
                   and item["column_names"] == ["server_number", "batch_id"] for item in unique):
            raise RuntimeError("Unexpected staged Votemap reminder batch uniqueness")
        return
    op.create_table(
        "votemap_reminder_clock",
        sa.Column("server_number", sa.Integer(), primary_key=True),
        sa.Column("completed_at", sa.Float(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_votemap_clock_server"),
        sa.CheckConstraint("outcome IN ('success', 'partial', 'failed')", name="ck_votemap_clock_outcome"),
    )
    op.create_table(
        "votemap_reminder_batch",
        sa.Column("server_number", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(100), primary_key=True),
        sa.Column("batch_id", sa.String(64), nullable=False),
        sa.Column("signature", sa.String(64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("completed_at", sa.Float(), nullable=True),
        sa.UniqueConstraint("server_number", "batch_id", name="uq_votemap_batch_server_id"),
        sa.CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_votemap_batch_server"),
        sa.CheckConstraint("status IN ('open', 'completed')", name="ck_votemap_batch_status"),
    )
    op.create_table(
        "votemap_reminder_delivery",
        sa.Column("server_number", sa.Integer(), primary_key=True),
        sa.Column("batch_id", sa.String(64), primary_key=True),
        sa.Column("player_id", sa.String(100), primary_key=True),
        sa.Column("token", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.Column("retry_at", sa.Float(), nullable=False),
        sa.CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_votemap_notice_server"),
        sa.CheckConstraint("status IN ('queued', 'sending', 'sent', 'rejected', 'unknown', 'skipped')", name="ck_votemap_notice_status"),
        sa.CheckConstraint("attempts >= 0", name="ck_votemap_notice_attempts"),
    )


def downgrade():
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT count(*) FROM votemap_reminder_batch WHERE status = 'open'")).scalar_one():
        raise RuntimeError("Resolve open Votemap reminder batches before downgrade")
    if connection.execute(sa.text("SELECT count(*) FROM votemap_reminder_delivery WHERE status IN ('sending', 'unknown')")).scalar_one():
        raise RuntimeError("Resolve or archive uncertain Votemap reminders before downgrade")
    op.drop_table("votemap_reminder_delivery")
    op.drop_table("votemap_reminder_batch")
    op.drop_table("votemap_reminder_clock")
