"""Retain disconnect events until their matching connect is recorded.

Revision ID: f3400a1b2c3d
Revises: f3520a1b2c3d
"""
from alembic import op
import sqlalchemy as sa

revision = "f3400a1b2c3d"
down_revision = "f3520a1b2c3d"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("unidentified_session_event"):
        op.create_table(
            "unidentified_session_event",
            sa.Column("fingerprint", sa.String(64), primary_key=True),
            sa.Column("server_number", sa.Integer(), nullable=False),
            sa.Column("event_kind", sa.String(16), nullable=False),
            sa.Column("event_us", sa.BigInteger(), nullable=False),
            sa.Column("player_name", sa.Text(), nullable=False),
            sa.Column("raw", sa.Text(), nullable=False),
            sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column("resolved_by", sa.String(150), nullable=True),
            sa.Column("resolution_reason", sa.Text(), nullable=True),
        )
        op.create_index("ix_unidentified_session_event_server_number", "unidentified_session_event", ["server_number"])
    else:
        columns = {column["name"] for column in inspector.get_columns("unidentified_session_event")}
        primary = set(inspector.get_pk_constraint("unidentified_session_event")["constrained_columns"])
        indexes = {index["name"] for index in inspector.get_indexes("unidentified_session_event")}
        if (columns != {"fingerprint", "server_number", "event_kind", "event_us", "player_name", "raw",
                        "resolved_at", "resolved_by", "resolution_reason"}
                or primary != {"fingerprint"} or "ix_unidentified_session_event_server_number" not in indexes):
            raise RuntimeError("Unexpected staged unidentified session schema")
    session_columns = {column["name"]: column for column in inspector.get_columns("player_sessions")}
    for name in ("start_event_us", "end_event_us"):
        if name not in session_columns:
            op.add_column("player_sessions", sa.Column(name, sa.BigInteger(), nullable=True))
        elif not isinstance(session_columns[name]["type"], sa.BigInteger) or not session_columns[name]["nullable"]:
            raise RuntimeError(f"Unexpected staged session event column: {name}")
    if not inspector.has_table("session_event_resolution"):
        op.create_table(
            "session_event_resolution",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("server_number", sa.Integer(), nullable=False),
            sa.Column("player_id", sa.String(100), nullable=False),
            sa.Column("event_kind", sa.String(16), nullable=False),
            sa.Column("event_us", sa.BigInteger(), nullable=False),
            sa.Column("decision", sa.String(16), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("session_id", sa.Integer(), nullable=True),
            sa.Column("actor", sa.String(150), nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        )
        op.create_index("ix_session_event_resolution_server_number", "session_event_resolution", ["server_number"])
    else:
        columns = {column["name"] for column in inspector.get_columns("session_event_resolution")}
        primary = set(inspector.get_pk_constraint("session_event_resolution")["constrained_columns"])
        indexes = {index["name"] for index in inspector.get_indexes("session_event_resolution")}
        if (columns != {"id", "server_number", "player_id", "event_kind", "event_us", "decision", "reason", "session_id", "actor", "created_at"}
                or primary != {"id"} or "ix_session_event_resolution_server_number" not in indexes):
            raise RuntimeError("Unexpected staged session event audit schema")
    for name, event_key, wall_time in (
        ("pending_player_disconnect", "ended_event_us", "ended_at"),
        ("pending_player_connect", "started_event_us", "started_at"),
    ):
        if inspector.has_table(name):
            column_info = {column["name"]: column for column in inspector.get_columns(name)}
            columns = set(column_info)
            primary = set(inspector.get_pk_constraint(name)["constrained_columns"])
            if (columns != {"server_number", "player_id", event_key, wall_time, "created_at"}
                    or primary != {"server_number", "player_id", event_key}
                    or not isinstance(column_info[event_key]["type"], sa.BigInteger)):
                raise RuntimeError(f"Unexpected staged session event schema: {name}")
            continue
        op.create_table(
            name,
            sa.Column("server_number", sa.Integer(), primary_key=True),
            sa.Column("player_id", sa.String(100), primary_key=True),
            sa.Column(event_key, sa.BigInteger(), primary_key=True),
            sa.Column(wall_time, sa.TIMESTAMP(), nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        )


def downgrade():
    op.drop_index("ix_unidentified_session_event_server_number", table_name="unidentified_session_event")
    op.drop_table("unidentified_session_event")
    op.drop_table("pending_player_connect")
    op.drop_table("pending_player_disconnect")
    op.drop_index("ix_session_event_resolution_server_number", table_name="session_event_resolution")
    op.drop_table("session_event_resolution")
    op.drop_column("player_sessions", "end_event_us")
    op.drop_column("player_sessions", "start_event_us")
