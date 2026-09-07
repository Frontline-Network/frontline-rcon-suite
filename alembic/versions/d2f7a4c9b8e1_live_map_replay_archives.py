"""Live-map round archives and explainable gameplay detections."""
import sqlalchemy as sa
from alembic import op

revision = "d2f7a4c9b8e1"
down_revision = "b7e9d5026a31"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "tactical_archive",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("round_id", sa.String(160), nullable=False),
        sa.Column("start_at", sa.Float(), nullable=False),
        sa.Column("end_at", sa.Float(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("retention_days", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(150), nullable=False),
        sa.Column("reason", sa.String(1000), nullable=False),
        sa.Column("incident_id", sa.String(36), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("estimated_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.UniqueConstraint("server_number", "round_id", name="uq_tactical_archive_server_round"),
    )
    op.create_index(
        "ix_tactical_archive_server_expiry",
        "tactical_archive",
        ["server_number", "expires_at"],
    )
    op.create_table(
        "tactical_detection",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("server_number", sa.Integer(), primary_key=True),
        sa.Column("round_id", sa.String(160), nullable=False),
        sa.Column("player_id", sa.String(100), nullable=False),
        sa.Column("player_name", sa.String(200), nullable=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("first_at", sa.Float(), nullable=False),
        sa.Column("last_at", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("rule_version", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("incident_id", sa.String(36), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_tactical_detection_server_time",
        "tactical_detection",
        ["server_number", "last_at"],
    )
    op.create_index(
        "ix_tactical_detection_server_round",
        "tactical_detection",
        ["server_number", "round_id"],
    )
    op.create_index(
        "ix_tactical_detection_expiry",
        "tactical_detection",
        ["expires_at"],
    )


def downgrade():
    op.drop_table("tactical_detection")
    op.drop_table("tactical_archive")
