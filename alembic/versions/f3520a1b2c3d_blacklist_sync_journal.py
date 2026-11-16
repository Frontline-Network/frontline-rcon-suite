"""Persist blacklist synchronization delivery per target server.

Revision ID: f3520a1b2c3d
Revises: e3150a1b2c3d
"""
from alembic import op
import sqlalchemy as sa

revision = "f3520a1b2c3d"
down_revision = "e3150a1b2c3d"
branch_labels = None
depends_on = None


def upgrade():
    # RCON3 can stage this additive table while the shared service still uses
    # the older Alembic revision. A later regular upgrade must recognize it.
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("blacklist_sync_delivery"):
        columns = {column["name"] for column in inspector.get_columns("blacklist_sync_delivery")}
        expected = {"id", "server_number", "command", "status", "reason", "created_at", "updated_at"}
        primary = set(inspector.get_pk_constraint("blacklist_sync_delivery")["constrained_columns"])
        indexes = {index["name"] for index in inspector.get_indexes("blacklist_sync_delivery")}
        checks = {check["name"] for check in inspector.get_check_constraints("blacklist_sync_delivery")}
        if (columns != expected or primary != {"id"} or
            not {"ix_blacklist_sync_delivery_server_number", "ix_blacklist_sync_delivery_status"}.issubset(indexes) or
            not {"ck_blacklist_sync_server", "ck_blacklist_sync_status"}.issubset(checks)):
            raise RuntimeError("Unexpected staged blacklist synchronization schema")
        return
    op.create_table(
        "blacklist_sync_delivery",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("command", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.CheckConstraint("server_number BETWEEN 1 AND 32", name="ck_blacklist_sync_server"),
        sa.CheckConstraint("status IN ('queued', 'sending', 'done', 'review', 'reviewed')", name="ck_blacklist_sync_status"),
    )
    op.create_index("ix_blacklist_sync_delivery_server_number", "blacklist_sync_delivery", ["server_number"])
    op.create_index("ix_blacklist_sync_delivery_status", "blacklist_sync_delivery", ["status"])


def downgrade():
    op.drop_index("ix_blacklist_sync_delivery_status", table_name="blacklist_sync_delivery")
    op.drop_index("ix_blacklist_sync_delivery_server_number", table_name="blacklist_sync_delivery")
    op.drop_table("blacklist_sync_delivery")
