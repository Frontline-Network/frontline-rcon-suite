"""Add explicit Barricade blacklist record provenance.

Revision ID: f3980a1b2c3d
Revises: f3970a1b2c3d
"""
from alembic import op
import sqlalchemy as sa

revision = 'f3980a1b2c3d'
down_revision = 'f3970a1b2c3d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('barricade_blacklist_ownership',
        sa.Column('record_id', sa.Integer, sa.ForeignKey('blacklist_record.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('server_number', sa.Integer, nullable=False),
        sa.Column('integration_id', sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(['server_number', 'integration_id'],
            ['barricade_scan_integration.server_number', 'barricade_scan_integration.integration_id'],
            ondelete='RESTRICT', name='fk_barricade_blacklist_owner_integration'),
        sa.CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_barricade_blacklist_owner_server'))


def downgrade():
    bind = op.get_bind()
    if bind.execute(sa.text('SELECT EXISTS (SELECT 1 FROM barricade_blacklist_ownership)')).scalar():
        raise RuntimeError('Refusing to discard Barricade blacklist ownership history')
    op.drop_table('barricade_blacklist_ownership')
