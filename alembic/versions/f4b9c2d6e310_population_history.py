"""Durable occupancy samples and manual seeding attempts."""

import sqlalchemy as sa
from alembic import op

revision = "f4b9c2d6e310"
down_revision = "e3a8b1c5d209"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "population_samples",
        sa.Column("server_number", sa.Integer(), primary_key=True),
        sa.Column("scheduled_at", sa.BigInteger(), primary_key=True),
        sa.Column("captured_at", sa.Float(), nullable=False),
        sa.Column("interval_seconds", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("player_count", sa.Integer()),
        sa.Column("max_players", sa.Integer()),
        sa.Column("map_name", sa.String(160)),
        sa.CheckConstraint("interval_seconds IN (15, 30, 60)"),
        sa.CheckConstraint(
            "(status = 'ok' AND player_count IS NOT NULL AND max_players IS NOT NULL "
            "AND player_count >= 0 AND max_players >= player_count) "
            "OR (status = 'rcon_error' AND player_count IS NULL AND max_players IS NULL)"
        ),
    )
    op.create_table(
        "population_seeding_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("active_server", sa.Integer(), unique=True),
        sa.Column("started_at", sa.Float(), nullable=False),
        sa.Column("ended_at", sa.Float()),
        sa.Column("seeder_count", sa.Integer()),
        sa.Column("created_by", sa.String(150), nullable=False),
        sa.Column("ended_by", sa.String(150)),
        sa.CheckConstraint("ended_at IS NULL OR ended_at >= started_at"),
        sa.CheckConstraint("seeder_count IS NULL OR seeder_count >= 0"),
    )
    op.create_index(
        "ix_population_seeding_server_start",
        "population_seeding_sessions",
        ["server_number", "started_at"],
    )


def downgrade():
    op.drop_table("population_seeding_sessions")
    op.drop_table("population_samples")
