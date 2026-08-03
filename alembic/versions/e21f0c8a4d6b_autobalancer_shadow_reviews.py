"""Autobalancer shadow proposal reviews

Revision ID: e21f0c8a4d6b
Revises: cd1106b12a7f
Create Date: 2026-08-03
"""

import sqlalchemy as sa
from alembic import op

revision = "e21f0c8a4d6b"
down_revision = "cd1106b12a7f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "autobalance_decisions",
        sa.Column("review_verdict", sa.String(), nullable=True),
    )
    op.add_column(
        "autobalance_decisions",
        sa.Column("review_category", sa.String(), nullable=True),
    )
    op.add_column(
        "autobalance_decisions",
        sa.Column("review_comment", sa.Text(), nullable=True),
    )
    op.add_column(
        "autobalance_decisions",
        sa.Column("reviewed_by", sa.String(), nullable=True),
    )
    op.add_column(
        "autobalance_decisions",
        sa.Column("reviewed_at", sa.TIMESTAMP(), nullable=True),
    )


def downgrade():
    op.drop_column("autobalance_decisions", "reviewed_at")
    op.drop_column("autobalance_decisions", "reviewed_by")
    op.drop_column("autobalance_decisions", "review_comment")
    op.drop_column("autobalance_decisions", "review_category")
    op.drop_column("autobalance_decisions", "review_verdict")
