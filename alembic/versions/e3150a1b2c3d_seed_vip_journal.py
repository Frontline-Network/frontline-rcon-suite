"""Persist seed observations and individual VIP grants.

Revision ID: e3150a1b2c3d
Revises: d3650a1b2c3d
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "e3150a1b2c3d"
down_revision = "d3650a1b2c3d"
branch_labels = None
depends_on = None


def upgrade():
    # A pilot may have installed these additive tables before advancing the
    # shared Alembic head. Verify that exact staged schema before accepting it.
    inspector = sa.inspect(op.get_bind())
    existing = [inspector.has_table(name) for name in ("seed_vip_cycle", "seed_vip_grant")]
    if any(existing):
        if not all(existing):
            raise RuntimeError("Incomplete staged Seed VIP schema")
        expected_columns = {
            "seed_vip_cycle": {"server_number", "preview", "generation", "phase", "eligible", "seeded_at", "updated_at"},
            "seed_vip_grant": {"id", "server_number", "preview", "generation", "player_id", "player_name", "status", "reward_seconds", "cumulative", "reward_time", "target", "description", "reason", "updated_at"},
        }
        for name, expected in expected_columns.items():
            if {col["name"] for col in inspector.get_columns(name)} != expected:
                raise RuntimeError(f"Unexpected staged Seed VIP schema: {name}")
        if set(inspector.get_pk_constraint("seed_vip_cycle")["constrained_columns"]) != {"server_number", "preview"}:
            raise RuntimeError("Unexpected staged Seed VIP cycle primary key")
        if set(inspector.get_pk_constraint("seed_vip_grant")["constrained_columns"]) != {"id"}:
            raise RuntimeError("Unexpected staged Seed VIP grant primary key")
        uniques = {constraint["name"] for constraint in inspector.get_unique_constraints("seed_vip_grant")}
        checks = {constraint["name"] for table in expected_columns for constraint in inspector.get_check_constraints(table)}
        indexes = {index["name"] for index in inspector.get_indexes("seed_vip_grant")}
        if ("uq_seed_vip_grant_cycle_player" not in uniques or
            not {"ck_seed_vip_cycle_phase", "ck_seed_vip_cycle_generation", "ck_seed_vip_grant_status", "ck_seed_vip_grant_reward_seconds"}.issubset(checks) or
            not {"ix_seed_vip_grant_server_number", "ix_seed_vip_grant_status"}.issubset(indexes)):
            raise RuntimeError("Unexpected staged Seed VIP constraints or indexes")
        return
    op.create_table(
        "seed_vip_cycle",
        sa.Column("server_number", sa.Integer(), primary_key=True),
        sa.Column("preview", sa.Boolean(), primary_key=True),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(16), nullable=False),
        sa.Column("eligible", JSONB(), nullable=False),
        sa.Column("seeded_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint("phase IN ('uninitialized', 'seeding', 'seeded')", name="ck_seed_vip_cycle_phase"),
        sa.CheckConstraint("generation >= 0", name="ck_seed_vip_cycle_generation"),
    )
    op.create_table(
        "seed_vip_grant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("preview", sa.Boolean(), nullable=False),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.String(100), nullable=False),
        sa.Column("player_name", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reward_seconds", sa.Float(), nullable=False),
        sa.Column("cumulative", sa.Boolean(), nullable=False),
        sa.Column("reward_time", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("target", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.UniqueConstraint("server_number", "preview", "generation", "player_id", name="uq_seed_vip_grant_cycle_player"),
        sa.CheckConstraint("status IN ('queued', 'prepared', 'confirmed', 'rejected', 'skipped', 'review', 'reviewed', 'preview')", name="ck_seed_vip_grant_status"),
        sa.CheckConstraint("reward_seconds >= 0", name="ck_seed_vip_grant_reward_seconds"),
    )
    op.create_index("ix_seed_vip_grant_server_number", "seed_vip_grant", ["server_number"])
    op.create_index("ix_seed_vip_grant_status", "seed_vip_grant", ["status"])


def downgrade():
    op.drop_table("seed_vip_grant")
    op.drop_table("seed_vip_cycle")
