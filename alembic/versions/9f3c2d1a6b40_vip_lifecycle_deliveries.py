"""add VIP lifecycle delivery history

Revision ID: 9f3c2d1a6b40
Revises: c9e1f4a7b2d6
Create Date: 2026-09-03
"""

import sqlalchemy as sa
from alembic import op

revision = "9f3c2d1a6b40"
down_revision = "c9e1f4a7b2d6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vip_lifecycle_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("server_family", sa.String(length=32), nullable=False),
        sa.Column("rule", sa.String(length=32), nullable=False),
        sa.Column("player_id_id", sa.Integer(), nullable=False),
        sa.Column("player_name", sa.String(), nullable=False),
        sa.Column("status_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("test_mode", sa.Boolean(), nullable=False),
        sa.Column("status_checked_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["player_id_id"], ["steam_id_64.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "server_family",
            "rule",
            "player_id_id",
            "status_fingerprint",
            name="unique_vip_lifecycle_status_delivery",
        ),
    )
    for column in (
        "server_number",
        "server_family",
        "rule",
        "player_id_id",
        "status_fingerprint",
        "status",
    ):
        op.create_index(
            f"ix_vip_lifecycle_deliveries_{column}",
            "vip_lifecycle_deliveries",
            [column],
        )


def downgrade():
    for column in reversed(
        (
            "server_number",
            "server_family",
            "rule",
            "player_id_id",
            "status_fingerprint",
            "status",
        )
    ):
        op.drop_index(
            f"ix_vip_lifecycle_deliveries_{column}",
            table_name="vip_lifecycle_deliveries",
        )
    op.drop_table("vip_lifecycle_deliveries")
