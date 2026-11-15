"""Serialize incident event ID allocation until the writing transaction ends.

Revision ID: d3650a1b2c3d
Revises: c9d4e6a81111
"""

from alembic import op

revision = "d3650a1b2c3d"
down_revision = "c9d4e6a81111"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    # Installing the trigger must not wait indefinitely behind live writers.
    op.execute("SET LOCAL lock_timeout = '2s'")
    # A sequence allocates before commit. The trigger allocates a replacement
    # ID only after taking a transaction-scoped lock, so every writer, including
    # an older application instance, participates in commit ordering. The
    # original default may consume a sequence value; gaps are harmless.
    op.execute("""
        CREATE FUNCTION frontline_order_incident_event_id() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM pg_advisory_xact_lock(1179405892, 365);
            NEW.id := nextval(pg_get_serial_sequence(TG_RELID::regclass::text, 'id'));
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER frontline_order_incident_event_id
        BEFORE INSERT ON admin_incident_event
        FOR EACH ROW EXECUTE FUNCTION frontline_order_incident_event_id()
    """)


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("DROP TRIGGER IF EXISTS frontline_order_incident_event_id ON admin_incident_event")
    op.execute("DROP FUNCTION IF EXISTS frontline_order_incident_event_id()")
