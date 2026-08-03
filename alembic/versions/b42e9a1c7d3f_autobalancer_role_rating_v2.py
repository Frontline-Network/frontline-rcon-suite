"""Autobalancer role-aware rating and shadow calibration

Revision ID: b42e9a1c7d3f
Revises: a91f7c2d4e10
Create Date: 2026-08-04
"""

import sqlalchemy as sa
from alembic import op

revision = "b42e9a1c7d3f"
down_revision = "a91f7c2d4e10"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "autobalance_decisions",
        sa.Column(
            "rating_model_version",
            sa.String(),
            nullable=False,
            server_default="legacy",
        ),
    )
    op.add_column(
        "autobalance_decisions",
        sa.Column(
            "strategy_version",
            sa.String(),
            nullable=False,
            server_default="legacy",
        ),
    )
    op.add_column(
        "autobalance_decisions",
        sa.Column("review_preferred_strategy", sa.String(), nullable=True),
    )
    op.add_column(
        "autobalance_decisions",
        sa.Column("review_preferred_player_id", sa.String(), nullable=True),
    )
    op.add_column(
        "autobalance_snapshots",
        sa.Column(
            "rating_model_version",
            sa.String(),
            nullable=False,
            server_default="legacy",
        ),
    )
    op.create_index(
        "ix_autobalance_snapshots_rating_model_version",
        "autobalance_snapshots",
        ["rating_model_version"],
    )

    op.create_table(
        "autobalance_player_role_stats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("round_id", sa.String(), nullable=False),
        sa.Column("map_name", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("role_family", sa.String(), nullable=False),
        sa.Column("first_seen", sa.TIMESTAMP(), nullable=False),
        sa.Column("last_seen", sa.TIMESTAMP(), nullable=False),
        sa.Column("time_seconds", sa.Integer(), nullable=False),
        sa.Column("kills", sa.Integer(), nullable=False),
        sa.Column("deaths", sa.Integer(), nullable=False),
        sa.Column("teamkills", sa.Integer(), nullable=False),
        sa.Column("combat", sa.Integer(), nullable=False),
        sa.Column("offense", sa.Integer(), nullable=False),
        sa.Column("defense", sa.Integer(), nullable=False),
        sa.Column("support", sa.Integer(), nullable=False),
        sa.Column("valid_intervals", sa.Integer(), nullable=False),
        sa.Column("ambiguous_intervals", sa.Integer(), nullable=False),
        sa.Column("invalid_intervals", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "server_number",
            "round_id",
            "player_id",
            "role_family",
            name="unique_autobalance_player_role_stats",
        ),
    )
    for column in (
        "server_number",
        "round_id",
        "map_name",
        "player_id",
        "role_family",
        "last_seen",
    ):
        op.create_index(
            f"ix_autobalance_player_role_stats_{column}",
            "autobalance_player_role_stats",
            [column],
        )


def downgrade():
    op.drop_table("autobalance_player_role_stats")
    op.drop_index(
        "ix_autobalance_snapshots_rating_model_version",
        table_name="autobalance_snapshots",
    )
    op.drop_column("autobalance_snapshots", "rating_model_version")
    op.drop_column("autobalance_decisions", "review_preferred_player_id")
    op.drop_column("autobalance_decisions", "review_preferred_strategy")
    op.drop_column("autobalance_decisions", "strategy_version")
    op.drop_column("autobalance_decisions", "rating_model_version")
