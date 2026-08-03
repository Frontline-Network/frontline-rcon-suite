"""Autobalancer historical analytics and durable snapshots

Revision ID: a91f7c2d4e10
Revises: e21f0c8a4d6b
Create Date: 2026-08-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a91f7c2d4e10"
down_revision = "e21f0c8a4d6b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "autobalance_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("round_id", sa.String(), nullable=False),
        sa.Column("captured_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("map_name", sa.String(), nullable=False),
        sa.Column("map_elapsed_seconds", sa.Integer(), nullable=False),
        sa.Column("time_remaining_seconds", sa.Integer(), nullable=False),
        sa.Column("allies_count", sa.Integer(), nullable=False),
        sa.Column("axis_count", sa.Integer(), nullable=False),
        sa.Column("counts_match", sa.Boolean(), nullable=False),
        sa.Column("fail_count", sa.Integer(), nullable=False),
        sa.Column("stable_map", sa.Boolean(), nullable=False),
        sa.Column("rating_confidence", sa.Float(), nullable=True),
        sa.Column(
            "players", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "server_number",
            "round_id",
            "captured_at",
            name="unique_autobalance_snapshot",
        ),
    )
    for column in ("server_number", "round_id", "captured_at", "map_name"):
        op.create_index(
            f"ix_autobalance_snapshots_{column}",
            "autobalance_snapshots",
            [column],
        )

    op.create_table(
        "autobalance_round_analyses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("map_id", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.String(), nullable=False),
        sa.Column("config_hash", sa.String(), nullable=False),
        sa.Column("analyzed_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column(
            "analysis", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.ForeignKeyConstraint(["map_id"], ["map_history.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "server_number",
            "map_id",
            "algorithm_version",
            "config_hash",
            name="unique_autobalance_round_analysis",
        ),
    )
    for column in (
        "server_number",
        "map_id",
        "algorithm_version",
        "config_hash",
        "analyzed_at",
        "status",
    ):
        op.create_index(
            f"ix_autobalance_round_analyses_{column}",
            "autobalance_round_analyses",
            [column],
        )


def downgrade():
    op.drop_table("autobalance_round_analyses")
    op.drop_table("autobalance_snapshots")
