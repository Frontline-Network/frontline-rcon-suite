"""Mobile incident context and multi-subject support.

Revision ID: c8a4e2f6b901
Revises: b7a1c2d3e4f5
"""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "c8a4e2f6b901"
down_revision = "b7a1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "admin_incident",
        sa.Column(
            "reporter_context",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.create_table(
        "admin_incident_subject",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("incident_id", sa.String(length=36), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("player_id", sa.String(length=100), nullable=True),
        sa.Column("team", sa.String(length=100), nullable=True),
        sa.Column("squad_name", sa.String(length=100), nullable=True),
        sa.Column("squad_id", sa.String(length=100), nullable=True),
        sa.Column("squad_type", sa.String(length=32), nullable=True),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("leader_player_id", sa.String(length=100), nullable=True),
        sa.Column("leader_name", sa.String(length=255), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("match_method", sa.String(length=64), nullable=True),
        sa.Column("matched_text", sa.String(length=255), nullable=True),
        sa.Column("parser_version", sa.String(length=32), nullable=True),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("confirmed_by", sa.String(length=150), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('player', 'squad')", name="ck_admin_incident_subject_kind"
        ),
        sa.CheckConstraint(
            "state IN ('suggested', 'confirmed', 'rejected')",
            name="ck_admin_incident_subject_state",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"], ["admin_incident.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("incident_id", "kind", "state", "player_id"):
        op.create_index(
            f"ix_admin_incident_subject_{column}",
            "admin_incident_subject",
            [column],
        )

    connection = op.get_bind()
    incident = sa.table(
        "admin_incident",
        sa.column("id", sa.String),
        sa.column("target_id", sa.String),
        sa.column("target_name", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    subject = sa.table(
        "admin_incident_subject",
        sa.column("id", sa.String),
        sa.column("incident_id", sa.String),
        sa.column("kind", sa.String),
        sa.column("state", sa.String),
        sa.column("is_primary", sa.Boolean),
        sa.column("display_name", sa.String),
        sa.column("player_id", sa.String),
        sa.column("snapshot", sa.JSON),
        sa.column("match_method", sa.String),
        sa.column("confidence", sa.Float),
        sa.column("parser_version", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    rows = connection.execute(
        sa.select(
            incident.c.id,
            incident.c.target_id,
            incident.c.target_name,
            incident.c.created_at,
            incident.c.updated_at,
        ).where(incident.c.target_id.is_not(None), incident.c.target_name.is_not(None))
    ).mappings()
    for row in rows:
        connection.execute(
            subject.insert().values(
                id=str(uuid.uuid4()),
                incident_id=row["id"],
                kind="player",
                state="confirmed",
                is_primary=True,
                display_name=row["target_name"],
                player_id=row["target_id"],
                snapshot={},
                match_method="legacy_target",
                confidence=1.0,
                parser_version="legacy",
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        )

    op.alter_column("admin_incident", "reporter_context", server_default=None)


def downgrade():
    op.drop_table("admin_incident_subject")
    op.drop_column("admin_incident", "reporter_context")
