"""Index audit history by creation time without blocking writes.

Revision ID: b8e3a1f4c6d2
Revises: a4c7e9f2b681
"""

from alembic import op

revision = "b8e3a1f4c6d2"
down_revision = "a4c7e9f2b681"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_audit_log_creation_time",
            "audit_log",
            ["creation_time"],
            unique=False,
            postgresql_concurrently=True,
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_audit_log_creation_time",
            table_name="audit_log",
            postgresql_concurrently=True,
        )
