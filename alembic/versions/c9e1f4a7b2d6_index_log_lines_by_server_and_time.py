"""Index log history by server and event time without blocking writes.

Revision ID: c9e1f4a7b2d6
Revises: 8d0f4a2c9b71
"""

from alembic import op

revision = "c9e1f4a7b2d6"
down_revision = "8d0f4a2c9b71"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.create_index(
            "ix_log_lines_server_event_time",
            "log_lines",
            ["server", "event_time"],
            unique=False,
            postgresql_concurrently=True,
        )


def downgrade():
    with op.get_context().autocommit_block():
        op.drop_index(
            "ix_log_lines_server_event_time",
            table_name="log_lines",
            postgresql_concurrently=True,
        )
