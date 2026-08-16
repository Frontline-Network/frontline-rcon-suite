"""Discord report delivery and AI moderation records.

Revision ID: d9c4a7f1b2e3
Revises: 70d823b91325
"""

import sqlalchemy as sa
from alembic import op

revision = "d9c4a7f1b2e3"
down_revision = "70d823b91325"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("ck_admin_incident_source", "admin_incident", type_="check")
    op.create_check_constraint(
        "ck_admin_incident_source",
        "admin_incident",
        "source IN ('chat', 'manual', 'ai_chat', 'ai_player_name')",
    )
    op.create_table(
        "admin_incident_discord_delivery",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id"], ["admin_incident_event.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(
        "ix_admin_incident_discord_delivery_event_id",
        "admin_incident_discord_delivery",
        ["event_id"],
        unique=True,
    )
    op.create_index(
        "ix_admin_incident_discord_delivery_next_attempt_at",
        "admin_incident_discord_delivery",
        ["next_attempt_at"],
    )
    op.create_index(
        "ix_admin_incident_discord_delivery_delivered_at",
        "admin_incident_discord_delivery",
        ["delivered_at"],
    )

    op.create_table(
        "moderation_analysis",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=36), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("player_id", sa.String(length=100), nullable=True),
        sa.Column("candidate_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("candidate_text", sa.Text(), nullable=True),
        sa.Column("analysis", sa.JSON(), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=64), nullable=False),
        sa.Column("policy_profile_id", sa.String(length=64), nullable=False),
        sa.Column("policy_version", sa.String(length=32), nullable=False),
        sa.Column("dedupe_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source IN ('report', 'ai_chat', 'ai_player_name')",
            name="ck_moderation_analysis_source",
        ),
        sa.CheckConstraint(
            "visibility IN ('incident', 'shadow', 'ignore')",
            name="ck_moderation_analysis_visibility",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["admin_incident.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "incident_id",
        "source",
        "player_id",
        "candidate_fingerprint",
        "visibility",
        "dedupe_until",
        "created_at",
    ):
        op.create_index(
            f"ix_moderation_analysis_{column}", "moderation_analysis", [column]
        )

    op.create_table(
        "moderation_candidate_outbox",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.String(length=100), nullable=True),
        sa.Column("player_name", sa.String(length=255), nullable=True),
        sa.Column("candidate_text", sa.Text(), nullable=False),
        sa.Column("candidate_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("matched_rule_ids", sa.JSON(), nullable=False),
        sa.Column("policy", sa.JSON(), nullable=False),
        sa.Column("shadow_only", sa.Boolean(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source IN ('ai_chat', 'ai_player_name')",
            name="ck_moderation_candidate_source",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in (
        "source",
        "server_number",
        "player_id",
        "candidate_fingerprint",
        "next_attempt_at",
        "analysis_received_at",
        "created_at",
    ):
        op.create_index(
            f"ix_moderation_candidate_outbox_{column}",
            "moderation_candidate_outbox",
            [column],
        )


def downgrade():
    op.drop_table("moderation_candidate_outbox")
    op.drop_table("moderation_analysis")
    op.drop_table("admin_incident_discord_delivery")
    op.drop_constraint("ck_admin_incident_source", "admin_incident", type_="check")
    op.create_check_constraint(
        "ck_admin_incident_source",
        "admin_incident",
        "source IN ('chat', 'manual')",
    )
