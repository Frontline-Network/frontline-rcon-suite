"""Installation-local voice report preferences and fixed-text translations."""

from alembic import op
import sqlalchemy as sa

revision = "v261119lang01"
down_revision = "f3970a1b2c3d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "voice_language_preference",
        sa.Column("identity", sa.String(120), primary_key=True),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("explicit", sa.Boolean(), nullable=False),
        sa.Column("updated", sa.Float(), nullable=False),
    )
    op.create_table(
        "voice_verified_identity",
        sa.Column("discord_id", sa.String(32), primary_key=True),
        sa.Column("game_id", sa.String(100), nullable=False, unique=True),
    )
    op.create_table(
        "voice_translation_cache",
        sa.Column("language", sa.String(16), primary_key=True),
        sa.Column("version", sa.String(24), primary_key=True),
        sa.Column("texts", sa.JSON(), nullable=False),
        sa.Column("next_attempt", sa.Float(), nullable=False),
    )


def downgrade():
    op.drop_table("voice_translation_cache")
    op.drop_table("voice_verified_identity")
    op.drop_table("voice_language_preference")
