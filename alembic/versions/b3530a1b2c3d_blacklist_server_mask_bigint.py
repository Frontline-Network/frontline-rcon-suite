"""Allow the complete unsigned 32-bit blacklist server mask.

Revision ID: b3530a1b2c3d
Revises: a3170a1b2c3d
"""
from alembic import op
import sqlalchemy as sa

revision = "b3530a1b2c3d"
down_revision = "a3170a1b2c3d"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("blacklist", "servers", existing_type=sa.Integer(),
                    type_=sa.BigInteger(), existing_nullable=True)


def downgrade():
    # PostgreSQL rejects the conversion instead of truncating masks containing
    # server 32. Operators must resolve those masks before a downgrade.
    op.alter_column("blacklist", "servers", existing_type=sa.BigInteger(),
                    type_=sa.Integer(), existing_nullable=True)
