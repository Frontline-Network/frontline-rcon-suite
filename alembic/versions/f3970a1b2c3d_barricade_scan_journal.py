"""Add durable outbound Barricade scan reservations.

Revision ID: f3970a1b2c3d
Revises: f7770a1b2c3d
"""
from alembic import op
import sqlalchemy as sa

revision = 'f3970a1b2c3d'
down_revision = 'f7770a1b2c3d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_index('ix_player_sessions_server_id_scan', 'player_sessions', ['server_number', 'id'])
    op.create_index('ix_player_sessions_server_open_id_scan', 'player_sessions', ['server_number', 'id'],
                    postgresql_where=sa.text('"end" IS NULL AND end_event_us IS NULL'))
    op.create_table(
        'barricade_scan_baseline',
        sa.Column('server_number', sa.Integer, primary_key=True),
        sa.Column('integration_id', sa.String(36), primary_key=True),
        sa.Column('player_session_id', sa.Integer, primary_key=True),
    )
    op.create_table(
        'barricade_scan_integration',
        sa.Column('server_number', sa.Integer, primary_key=True),
        sa.Column('integration_id', sa.String(36), primary_key=True),
        sa.Column('credential_id', sa.Integer, nullable=False),
        sa.Column('registered_at_us', sa.BigInteger, nullable=False),
        sa.CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_barricade_integration_server'),
        sa.CheckConstraint('credential_id > 0', name='ck_barricade_integration_credential'),
    )
    op.create_table(
        'barricade_scan_integration_audit',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('server_number', sa.Integer, nullable=False),
        sa.Column('integration_id', sa.String(36), nullable=False),
        sa.Column('old_credential_id', sa.Integer, nullable=True),
        sa.Column('new_credential_id', sa.Integer, nullable=False),
        sa.Column('actor', sa.String(150), nullable=False),
        sa.Column('reason', sa.String(1000), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_table(
        'barricade_scan_review_audit',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('delivery_id', sa.Integer, nullable=False),
        sa.Column('server_number', sa.Integer, nullable=False),
        sa.Column('integration_id', sa.String(128), nullable=False),
        sa.Column('decision', sa.String(16), nullable=False),
        sa.Column('actor', sa.String(150), nullable=False),
        sa.Column('reason', sa.String(1000), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_table(
        'barricade_scan_delivery',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('server_number', sa.Integer, nullable=False),
        sa.Column('integration_id', sa.String(128), nullable=False),
        sa.Column('player_session_id', sa.Integer, nullable=False),
        sa.Column('player_id', sa.String(100), nullable=False),
        sa.Column('game', sa.String(8), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('review_cause', sa.String(32), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.UniqueConstraint('server_number', 'integration_id', 'player_session_id', name='uq_barricade_scan_session'),
        sa.CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_barricade_scan_server'),
        sa.CheckConstraint("game IN ('HLL', 'HLLV')", name='ck_barricade_scan_game'),
        sa.CheckConstraint("status IN ('queued', 'sending', 'done', 'review', 'reviewed')", name='ck_barricade_scan_status'),
    )


def downgrade():
    if op.get_bind().execute(sa.text('SELECT EXISTS (SELECT 1 FROM barricade_scan_baseline) OR EXISTS (SELECT 1 FROM barricade_scan_delivery) OR EXISTS (SELECT 1 FROM barricade_scan_integration) OR EXISTS (SELECT 1 FROM barricade_scan_integration_audit) OR EXISTS (SELECT 1 FROM barricade_scan_review_audit)')).scalar():
        raise RuntimeError('Cannot remove Barricade scan delivery history; it prevents duplicate scans')
    op.drop_table('barricade_scan_delivery')
    op.drop_table('barricade_scan_integration')
    op.drop_table('barricade_scan_baseline')
    op.drop_index('ix_player_sessions_server_open_id_scan', table_name='player_sessions')
    op.drop_index('ix_player_sessions_server_id_scan', table_name='player_sessions')
    op.drop_table('barricade_scan_integration_audit')
    op.drop_table('barricade_scan_review_audit')
