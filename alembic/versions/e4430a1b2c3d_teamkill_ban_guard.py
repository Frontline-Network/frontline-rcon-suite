"""Persist teamkill ban reservations and their review history.

Revision ID: e4430a1b2c3d
Revises: d3330a1b2c3d
"""
from alembic import op
import sqlalchemy as sa

revision = "e4430a1b2c3d"
down_revision = "d3330a1b2c3d"
branch_labels = None
depends_on = None


def _tables():
    # Migrations are immutable: do not import runtime models that can change.
    metadata = sa.MetaData()
    sa.Table('teamkill_ban_cutover', metadata,
        sa.Column('server_number', sa.Integer, primary_key=True),
        sa.Column('event_ms', sa.BigInteger, nullable=False),
        sa.CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_tk_cutover_server'))
    sa.Table('teamkill_ban_guard', metadata,
        sa.Column('server_number', sa.Integer, primary_key=True),
        sa.Column('player_id', sa.String(100), primary_key=True),
        sa.Column('connection_ms', sa.BigInteger, primary_key=True),
        sa.Column('token', sa.String(35), nullable=False),
        sa.Column('state', sa.String(16), nullable=False, index=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reviewed_by', sa.String(150)), sa.Column('review_reason', sa.Text),
        sa.CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_tk_guard_server'),
        sa.CheckConstraint("state IN ('pending', 'confirmed', 'rejected', 'reviewed')", name='ck_tk_guard_state'),
        sa.UniqueConstraint('token', name='uq_tk_guard_token'))
    sa.Table('teamkill_ban_guard_history', metadata,
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('server_number', sa.Integer, nullable=False, index=True),
        sa.Column('player_id', sa.String(100), nullable=False),
        sa.Column('token', sa.String(35), nullable=False, index=True),
        sa.Column('event', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actor', sa.String(150)), sa.Column('reason', sa.Text),
        sa.CheckConstraint('server_number BETWEEN 1 AND 32', name='ck_tk_history_server'),
        sa.CheckConstraint("event IN ('reserved', 'confirmed', 'rejected', 'reviewed')", name='ck_tk_history_event'))
    return metadata


def upgrade():
    metadata = _tables()
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    present = [inspector.has_table(name) for name in metadata.tables]
    if any(present):
        # A partially staged migration is unsafe. An already staged full
        # schema must also match the expected columns and constraints.
        if not all(present):
            raise RuntimeError("Teamkill ban guard staging is incomplete")
        for table in metadata.sorted_tables:
            columns = {item['name']: item for item in inspector.get_columns(table.name)}
            if set(columns) != set(table.columns.keys()):
                raise RuntimeError(f"Unexpected teamkill guard columns: {table.name}")
            for expected in table.columns:
                actual = columns[expected.name]
                if (actual['type']._type_affinity is not expected.type._type_affinity
                        or actual['nullable'] != expected.nullable
                        or getattr(actual['type'], 'length', None) != getattr(expected.type, 'length', None)):
                    raise RuntimeError(f"Unexpected teamkill guard column: {table.name}.{expected.name}")
            if set(inspector.get_pk_constraint(table.name)['constrained_columns']) != {c.name for c in table.primary_key}:
                raise RuntimeError(f"Unexpected teamkill guard primary key: {table.name}")
            checks = {item['name'] for item in inspector.get_check_constraints(table.name)}
            expected_checks = {c.name for c in table.constraints if isinstance(c, sa.CheckConstraint)}
            if not expected_checks.issubset(checks):
                raise RuntimeError(f"Missing teamkill guard checks: {table.name}")
            uniques = {item['name'] for item in inspector.get_unique_constraints(table.name)}
            expected_uniques = {c.name for c in table.constraints if isinstance(c, sa.UniqueConstraint)}
            if not expected_uniques.issubset(uniques):
                raise RuntimeError(f"Missing teamkill guard unique constraints: {table.name}")
            indexes = {item['name'] for item in inspector.get_indexes(table.name)}
            if not {i.name for i in table.indexes}.issubset(indexes):
                raise RuntimeError(f"Missing teamkill guard indexes: {table.name}")
        return
    metadata.create_all(bind=bind, checkfirst=False)


def downgrade():
    metadata = _tables()
    bind = op.get_bind()
    # Do not silently discard pending actions or audit history.
    for table in metadata.sorted_tables:
        if bind.execute(sa.select(sa.literal(1)).select_from(table).limit(1)).first():
            raise RuntimeError("Teamkill guard contains data; retain it during rollback")
    metadata.drop_all(bind=bind, checkfirst=False)
