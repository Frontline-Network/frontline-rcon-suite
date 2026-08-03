"""Autobalancer decision audit records

Revision ID: cd1106b12a7f
Revises: 89a3502370a0
Create Date: 2026-08-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "cd1106b12a7f"
down_revision = "89a3502370a0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "autobalance_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("decision_id", sa.String(), nullable=False),
        sa.Column("incident_id", sa.String(), nullable=False),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("round_id", sa.String(), nullable=False),
        sa.Column("round_started_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("mode", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("source_team", sa.String(), nullable=False),
        sa.Column("target_team", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=True),
        sa.Column("player_name", sa.String(), nullable=True),
        sa.Column("volunteer", sa.Boolean(), nullable=False),
        sa.Column("protection_tier", sa.Integer(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("rating_confidence", sa.Float(), nullable=True),
        sa.Column("reason", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "before_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "after_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("executed_at", sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("decision_id", name="unique_autobalance_decision_id"),
    )
    for column in (
        "created_at",
        "decision_id",
        "incident_id",
        "player_id",
        "round_id",
        "server_number",
        "status",
    ):
        op.create_index(
            f"ix_autobalance_decisions_{column}",
            "autobalance_decisions",
            [column],
        )


def downgrade():
    op.drop_table("autobalance_decisions")
