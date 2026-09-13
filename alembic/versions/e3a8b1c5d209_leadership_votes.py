"""Durable, opt-in leadership votes and private message outbox."""

import sqlalchemy as sa
from alembic import op

revision = "e3a8b1c5d209"
down_revision = "d2f7a4c9b8e1"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "leadership_presence",
        sa.Column("server_number", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.String(100), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_table(
        "leadership_vote",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("team", sa.String(16), nullable=False),
        sa.Column("target_id", sa.String(100), nullable=False),
        sa.Column("reporter_id", sa.String(100), nullable=False),
        sa.Column("round_id", sa.String(200), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("slot", sa.String(60), nullable=True, unique=True),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("ended_at", sa.Float()),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    for field in ("server_number", "target_id", "reporter_id", "status"):
        op.create_index(f"ix_leadership_vote_{field}", "leadership_vote", [field])
    op.create_table(
        "leadership_message",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column(
            "vote_id",
            sa.String(36),
            sa.ForeignKey("leadership_vote.id", ondelete="CASCADE"),
        ),
        sa.Column("player_id", sa.String(100), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("sent_at", sa.Float()),
    )
    for field in ("server_number", "vote_id", "status"):
        op.create_index(f"ix_leadership_message_{field}", "leadership_message", [field])
    op.add_column("admin_incident", sa.Column("leadership_vote_id", sa.String(36)))
    op.add_column("admin_incident", sa.Column("leadership_vote", sa.JSON()))
    op.create_index(
        "ix_admin_incident_leadership_vote_id", "admin_incident", ["leadership_vote_id"]
    )


def downgrade():
    op.drop_index("ix_admin_incident_leadership_vote_id", "admin_incident")
    op.drop_column("admin_incident", "leadership_vote")
    op.drop_column("admin_incident", "leadership_vote_id")
    op.drop_table("leadership_message")
    op.drop_table("leadership_vote")
    op.drop_table("leadership_presence")
