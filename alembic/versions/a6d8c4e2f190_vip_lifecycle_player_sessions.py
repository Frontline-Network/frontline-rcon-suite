"""deliver VIP lifecycle campaigns once per player session

Revision ID: a6d8c4e2f190
Revises: 9f3c2d1a6b40
Create Date: 2026-09-03
"""

import sqlalchemy as sa
from alembic import op

revision = "a6d8c4e2f190"
down_revision = "9f3c2d1a6b40"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "vip_lifecycle_deliveries",
        sa.Column("player_session_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "vip_lifecycle_deliveries",
        sa.Column("last_attempt_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_vip_lifecycle_deliveries_player_session",
        "vip_lifecycle_deliveries",
        "player_sessions",
        ["player_session_id"],
        ["id"],
    )
    op.create_index(
        "ix_vip_lifecycle_deliveries_player_session_id",
        "vip_lifecycle_deliveries",
        ["player_session_id"],
    )
    op.create_unique_constraint(
        "unique_vip_lifecycle_delivery_session",
        "vip_lifecycle_deliveries",
        ["server_number", "rule", "player_session_id", "test_mode"],
    )


def downgrade():
    op.drop_constraint(
        "unique_vip_lifecycle_delivery_session",
        "vip_lifecycle_deliveries",
        type_="unique",
    )
    op.drop_index(
        "ix_vip_lifecycle_deliveries_player_session_id",
        table_name="vip_lifecycle_deliveries",
    )
    op.drop_constraint(
        "fk_vip_lifecycle_deliveries_player_session",
        "vip_lifecycle_deliveries",
        type_="foreignkey",
    )
    op.drop_column("vip_lifecycle_deliveries", "last_attempt_at")
    op.drop_column("vip_lifecycle_deliveries", "player_session_id")
