"""Mobile admin incident inbox

Revision ID: b7a1c2d3e4f5
Revises: 89a3502370a0
"""

import sqlalchemy as sa
from alembic import op

revision = "b7a1c2d3e4f5"
down_revision = "89a3502370a0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "admin_incident",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reporter_id", sa.String(length=100), nullable=True),
        sa.Column("reporter_name", sa.String(length=255), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("target_name", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("raw_message", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.String(length=150), nullable=True),
        sa.Column("dedupe_key", sa.String(length=64), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "source IN ('chat', 'manual')", name="ck_admin_incident_source"
        ),
        sa.CheckConstraint(
            "status IN ('new', 'claimed', 'resolved', 'dismissed')",
            name="ck_admin_incident_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "server_number",
        "status",
        "reporter_id",
        "target_id",
        "assigned_to",
        "dedupe_key",
        "created_at",
        "updated_at",
    ):
        op.create_index(
            f"ix_admin_incident_{column}", "admin_incident", [column], unique=False
        )

    op.create_table(
        "admin_incident_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incident_id", sa.String(length=36), nullable=False),
        sa.Column("actor", sa.String(length=150), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["admin_incident.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key"),
    )
    for column in ("incident_id", "event_type", "idempotency_key", "created_at"):
        op.create_index(
            f"ix_admin_incident_event_{column}",
            "admin_incident_event",
            [column],
            unique=False,
        )

    op.create_table(
        "admin_incident_push_delivery",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"], ["admin_incident_event.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "device_id", name="unique_push_event_device"),
    )
    op.create_index(
        "ix_admin_incident_push_delivery_event_id",
        "admin_incident_push_delivery",
        ["event_id"],
    )
    op.create_index(
        "ix_admin_incident_push_delivery_device_id",
        "admin_incident_push_delivery",
        ["device_id"],
    )


def downgrade():
    op.drop_table("admin_incident_push_delivery")
    op.drop_table("admin_incident_event")
    op.drop_table("admin_incident")
