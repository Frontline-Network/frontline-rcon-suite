"""Persist event-scoped automod reservations.

Revision ID: f4440a1b2c3d
Revises: e4430a1b2c3d
"""
from alembic import op
import sqlalchemy as sa

revision = 'f4440a1b2c3d'
down_revision = 'e4430a1b2c3d'
branch_labels = None
depends_on = None


def _tables():
    metadata = sa.MetaData()
    sa.Table('automod_event_cutover', metadata,
        sa.Column('server_number', sa.Integer, primary_key=True),
        sa.Column('boundary_ms', sa.BigInteger, nullable=False),
        sa.Column('cleanup_ms', sa.BigInteger, nullable=False),
        sa.CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_automod_event_cutover_server'))
    sa.Table('automod_event_action', metadata,
        sa.Column('server_number', sa.Integer, primary_key=True),
        sa.Column('player_id', sa.String(100), primary_key=True),
        sa.Column('event_key', sa.String(64), primary_key=True),
        sa.Column('rule', sa.String(150), primary_key=True),
        sa.Column('action', sa.String(20), primary_key=True),
        sa.Column('event_ms', sa.BigInteger, nullable=False, index=True),
        sa.Column('token', sa.String(32), nullable=False, index=True),
        sa.Column('state', sa.String(20), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_automod_event_action_server'),
        sa.CheckConstraint("action IN ('message', 'punish', 'kick')", name='ck_automod_event_action_kind'),
        sa.CheckConstraint("state IN ('pending', 'confirmed', 'rejected', 'reviewed')", name='ck_automod_event_action_state'))
    return metadata


def upgrade():
    metadata = _tables()
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    present = [inspector.has_table(name) for name in metadata.tables]
    if any(present):
        if not all(present):
            raise RuntimeError('Automod event staging is incomplete')
        for table in metadata.sorted_tables:
            columns = {item['name']: item for item in inspector.get_columns(table.name)}
            if set(columns) != set(table.columns.keys()):
                raise RuntimeError(f'Unexpected automod event columns: {table.name}')
            for expected in table.columns:
                actual = columns[expected.name]
                if (actual['type']._type_affinity is not expected.type._type_affinity
                        or actual['nullable'] != expected.nullable
                        or getattr(actual['type'], 'length', None) != getattr(expected.type, 'length', None)):
                    raise RuntimeError(f'Unexpected automod event column: {table.name}.{expected.name}')
            if set(inspector.get_pk_constraint(table.name)['constrained_columns']) != {c.name for c in table.primary_key}:
                raise RuntimeError(f'Unexpected automod event primary key: {table.name}')
            checks = {item['name'] for item in inspector.get_check_constraints(table.name)}
            if not {c.name for c in table.constraints if isinstance(c, sa.CheckConstraint)}.issubset(checks):
                raise RuntimeError(f'Missing automod event checks: {table.name}')
            indexes = {item['name'] for item in inspector.get_indexes(table.name)}
            if not {i.name for i in table.indexes}.issubset(indexes):
                raise RuntimeError(f'Missing automod event indexes: {table.name}')
        return
    metadata.create_all(bind=bind, checkfirst=False)


def downgrade():
    metadata = _tables()
    bind = op.get_bind()
    for table in metadata.sorted_tables:
        if bind.execute(sa.select(sa.literal(1)).select_from(table).limit(1)).first():
            raise RuntimeError('Automod event guard contains data; retain it during rollback')
    metadata.drop_all(bind=bind, checkfirst=False)
