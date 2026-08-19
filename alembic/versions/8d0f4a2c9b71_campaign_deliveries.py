"""add durable campaign deliveries

Revision ID: 8d0f4a2c9b71
Revises: b8e3a1f4c6d2
Create Date: 2026-08-19
"""

import sqlalchemy as sa
from alembic import op

revision = "8d0f4a2c9b71"
down_revision = "b8e3a1f4c6d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "campaign_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("campaign_id", sa.String(length=64), nullable=False),
        sa.Column("player_id_id", sa.Integer(), nullable=False),
        sa.Column("player_session_id", sa.Integer(), nullable=False),
        sa.Column("player_name", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("eligible_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("next_attempt_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("last_attempt_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("sent_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["player_id_id"], ["steam_id_64.id"]),
        sa.ForeignKeyConstraint(["player_session_id"], ["player_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "server_number",
            "campaign_id",
            "player_session_id",
            name="unique_campaign_delivery_session",
        ),
    )
    op.create_index(
        "ix_campaign_deliveries_server_number",
        "campaign_deliveries",
        ["server_number"],
    )
    op.create_index(
        "ix_campaign_deliveries_campaign_id",
        "campaign_deliveries",
        ["campaign_id"],
    )
    op.create_index(
        "ix_campaign_deliveries_player_id_id",
        "campaign_deliveries",
        ["player_id_id"],
    )
    op.create_index(
        "ix_campaign_deliveries_player_session_id",
        "campaign_deliveries",
        ["player_session_id"],
    )
    op.create_index(
        "ix_campaign_deliveries_status",
        "campaign_deliveries",
        ["status"],
    )
    op.create_index(
        "ix_campaign_deliveries_eligible_at",
        "campaign_deliveries",
        ["eligible_at"],
    )


def downgrade():
    op.drop_index(
        "ix_campaign_deliveries_eligible_at", table_name="campaign_deliveries"
    )
    op.drop_index("ix_campaign_deliveries_status", table_name="campaign_deliveries")
    op.drop_index(
        "ix_campaign_deliveries_player_session_id",
        table_name="campaign_deliveries",
    )
    op.drop_index(
        "ix_campaign_deliveries_player_id_id", table_name="campaign_deliveries"
    )
    op.drop_index(
        "ix_campaign_deliveries_campaign_id", table_name="campaign_deliveries"
    )
    op.drop_index(
        "ix_campaign_deliveries_server_number", table_name="campaign_deliveries"
    )
    op.drop_table("campaign_deliveries")
