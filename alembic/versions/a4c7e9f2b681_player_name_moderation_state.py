"""Remember the last AI-checked player name per stable player identity.

Revision ID: a4c7e9f2b681
Revises: d9c4a7f1b2e3
"""

import sqlalchemy as sa
from alembic import op

revision = "a4c7e9f2b681"
down_revision = "d9c4a7f1b2e3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "player_name_moderation_state",
        sa.Column("player_id", sa.String(length=100), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("policy_profile_id", sa.String(length=64), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("candidate_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("player_id"),
    )


def downgrade():
    op.drop_table("player_name_moderation_state")
