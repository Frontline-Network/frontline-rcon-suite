"""Private intake and delivery for the Discord player panel."""

from alembic import op
import sqlalchemy as sa

revision = "v261119voice02"
down_revision = "v261119lang01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "voice_player_draft",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("server", sa.Integer(), nullable=False),
        sa.Column("discord_id", sa.String(24), nullable=False),
        sa.Column("message", sa.String(2000), nullable=False),
        sa.Column("language", sa.String(40), nullable=False),
        sa.Column("expires", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_voice_player_draft_expires", "voice_player_draft", ["expires"])
    op.create_table(
        "voice_link_challenge",
        sa.Column("server", sa.Integer(), primary_key=True),
        sa.Column("discord_id", sa.String(24), primary_key=True),
        sa.Column("game_id", sa.String(100), nullable=False),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("delivered", sa.Boolean(), nullable=False),
    )
    op.create_index(
        "ix_voice_challenge_target",
        "voice_link_challenge",
        ["server", "game_id", "created"],
    )
    op.create_table(
        "voice_player_delivery",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "incident_id",
            sa.String(36),
            sa.ForeignKey("admin_incident.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("discord_id", sa.String(24), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False),
        sa.Column("due", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "uq_voice_delivery_recipient",
        "voice_player_delivery",
        ["incident_id", "discord_id", "kind"],
        unique=True,
    )
    op.create_index("ix_voice_delivery_due", "voice_player_delivery", ["done", "due"])


def downgrade():
    op.drop_table("voice_player_delivery")
    op.drop_table("voice_link_challenge")
    op.drop_table("voice_player_draft")
