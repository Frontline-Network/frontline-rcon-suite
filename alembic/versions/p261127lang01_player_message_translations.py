"""Add recipient-template translations and original/delivered text audit."""
import sqlalchemy as sa
from alembic import op

revision = "p261127lang01"
down_revision = "c261127wh001"
branch_labels = depends_on = None


def upgrade():
    op.create_index('ix_voice_language_preference_identity_lower','voice_language_preference',[sa.text('lower(identity)')],if_not_exists=True)
    op.create_index('ix_voice_verified_identity_game_lower','voice_verified_identity',[sa.text('lower(game_id)')],if_not_exists=True)
    op.create_table("player_message_translation",
        sa.Column("key", sa.String(160), primary_key=True),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("source_content", sa.Text(), nullable=False),
        sa.Column("translations", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.String(150), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False))
    op.create_index("ix_player_message_translation_source_hash", "player_message_translation", ["source_hash"])
    op.create_table("player_message_localization_audit",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("template_key", sa.String(160), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("original", sa.Text(), nullable=False),
        sa.Column("delivered", sa.Text(), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False))
    op.create_index("ix_player_message_localization_audit_player_id", "player_message_localization_audit", ["player_id"])


def downgrade():
    bind = op.get_bind()
    if any(bind.execute(sa.text("SELECT count(*) FROM " + table)).scalar() for table in
           ("player_message_translation", "player_message_localization_audit")):
        raise RuntimeError("Retain player translations and delivery audit; roll back application code without dropping these additive tables")
    op.drop_table("player_message_localization_audit")
    op.drop_table("player_message_translation")
    op.drop_index('ix_voice_verified_identity_game_lower',table_name='voice_verified_identity')
    op.drop_index('ix_voice_language_preference_identity_lower',table_name='voice_language_preference')
