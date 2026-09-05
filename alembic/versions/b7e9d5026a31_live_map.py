"""Private live-map history and evidence, additive and disabled by default."""
from alembic import op
import sqlalchemy as sa

revision = "b7e9d5026a31"
down_revision = "a6d8c4e2f190"
branch_labels = depends_on = None


def upgrade():
    op.create_table("tactical_settings", sa.Column("server_number", sa.Integer(), primary_key=True), sa.Column("value", sa.JSON(), nullable=False))
    op.create_table("tactical_block", sa.Column("id", sa.String(36), primary_key=True),
                    sa.Column("server_number", sa.Integer(), nullable=False), sa.Column("round_id", sa.String(160), nullable=False),
                    sa.Column("start_at", sa.Float(), nullable=False), sa.Column("end_at", sa.Float(), nullable=False), sa.Column("data", sa.LargeBinary(), nullable=False))
    op.create_index("ix_tactical_block_server_time", "tactical_block", ["server_number", "end_at"])
    op.create_index("ix_tactical_block_server_round_time", "tactical_block", ["server_number", "round_id", "start_at"])
    op.create_table("tactical_review", sa.Column("server_number", sa.Integer(), primary_key=True),
                    sa.Column("signal_id", sa.String(64), primary_key=True), sa.Column("incident_id", sa.String(36), nullable=False),
                    sa.Column("expires_at", sa.Float(), nullable=False), sa.Column("evidence", sa.LargeBinary(), nullable=True))
    op.create_index("ix_tactical_review_expires_at", "tactical_review", ["expires_at"])


def downgrade():
    for table in ("tactical_review", "tactical_block", "tactical_settings"):
        op.drop_table(table)
