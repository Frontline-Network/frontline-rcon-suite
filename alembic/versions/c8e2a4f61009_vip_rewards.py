"""Durable additional VIP rewards, separate from Seed-VIP."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "c8e2a4f61009"
down_revision = "c8a4e2f6b901"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vip_reward_state",
        sa.Column("server_number", sa.Integer(), primary_key=True),
        sa.Column("preview", sa.Boolean(), primary_key=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
    )
    op.create_table(
        "vip_reward_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("preview", sa.Boolean(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("processed", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("server_number", "preview", "key"),
    )
    op.create_index(
        "ix_vip_reward_event_server_number", "vip_reward_event", ["server_number"]
    )
    op.create_index("ix_vip_reward_event_processed", "vip_reward_event", ["processed"])
    op.create_table(
        "vip_reward_grant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("preview", sa.Boolean(), nullable=False),
        sa.Column("player_id", sa.String(100), nullable=False),
        sa.Column("rule", sa.String(100), nullable=False),
        sa.Column("trigger", sa.String(160), nullable=False),
        sa.Column("occurred", sa.Float(), nullable=False),
        sa.Column("requested_seconds", sa.Float(), nullable=False),
        sa.Column("credited_seconds", sa.Float(), nullable=False),
        sa.Column("limit", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("target", sa.String(64), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("written_at", sa.Float(), nullable=True),
        sa.UniqueConstraint("server_number", "preview", "player_id", "rule", "trigger"),
    )
    for name in ("server_number", "player_id", "status"):
        op.create_index("ix_vip_reward_grant_" + name, "vip_reward_grant", [name])


def downgrade():
    op.drop_table("vip_reward_grant")
    op.drop_table("vip_reward_event")
    op.drop_table("vip_reward_state")
