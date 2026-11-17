"""Permit durable reservations for automatic Vietnam VIP restoration.

Revision ID: f7770a1b2c3d
Revises: f6660a1b2c3d
"""
import re

from alembic import op
import sqlalchemy as sa

revision = 'f7770a1b2c3d'
down_revision = 'f6660a1b2c3d'
branch_labels = None
depends_on = None

TABLE = 'automod_action_guard'
CONSTRAINT = 'ck_automod_guard_action'
OLD = {'message', 'punish', 'kick', 'switch', 'ban'}
NEW = OLD | {'vip'}


def _set_allowed(target):
    bind = op.get_bind()
    matches = [item for item in sa.inspect(bind).get_check_constraints(TABLE)
               if item['name'] == CONSTRAINT]
    if len(matches) != 1:
        raise RuntimeError('Automatic action guard constraint is missing or ambiguous')
    values = set(re.findall(r"'([^']+)'", matches[0]['sqltext']))
    if values == target:
        return
    if values not in (OLD, NEW):
        raise RuntimeError('Unexpected automatic action guard constraint')
    if target == OLD and bind.execute(sa.text(
            "SELECT 1 FROM automod_action_guard WHERE action = 'vip' LIMIT 1")).first():
        raise RuntimeError('VIP reservations exist; retain the expanded constraint')
    expression = "action IN ('message', 'punish', 'kick', 'switch', 'ban', 'vip')" if target == NEW else \
                 "action IN ('message', 'punish', 'kick', 'switch', 'ban')"
    with op.batch_alter_table(TABLE) as batch:
        batch.drop_constraint(CONSTRAINT, type_='check')
        batch.create_check_constraint(CONSTRAINT, expression)


def upgrade():
    _set_allowed(NEW)


def downgrade():
    _set_allowed(OLD)
