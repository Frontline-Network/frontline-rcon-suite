"""Track VIP reward notices independently of the grant itself.

Revision ID: c3230a1b2c3d
Revises: b3530a1b2c3d
"""
from alembic import op
import sqlalchemy as sa

revision = "c3230a1b2c3d"
down_revision = "b3530a1b2c3d"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("vip_reward_notice"):
        columns = {column["name"]: column for column in inspector.get_columns("vip_reward_notice")}
        expected = {"grant_id", "server_number", "player_id", "message", "status", "attempts", "created_at", "due_at", "expires_at", "updated_at"}
        indexes = {index["name"] for index in inspector.get_indexes("vip_reward_notice")}
        checks = {check["name"] for check in inspector.get_check_constraints("vip_reward_notice")}
        foreign_keys = inspector.get_foreign_keys("vip_reward_notice")
        expected_types = {
            "grant_id": sa.Integer, "server_number": sa.Integer, "player_id": sa.String,
            "message": sa.Text, "status": sa.String, "attempts": sa.Integer,
            "created_at": sa.Float, "due_at": sa.Float, "expires_at": sa.Float,
            "updated_at": sa.Float,
        }
        if (set(columns) != expected or any(column["nullable"] for column in columns.values())
                or any(not isinstance(columns[name]["type"], expected_type)
                       for name, expected_type in expected_types.items() if name in columns)
                or ("player_id" in columns and columns["player_id"]["type"].length != 100)
                or ("status" in columns and columns["status"]["type"].length != 16)
                or set(inspector.get_pk_constraint("vip_reward_notice")["constrained_columns"]) != {"grant_id"}
                or not {"ix_vip_reward_notice_server_number", "ix_vip_reward_notice_status"}.issubset(indexes)
                or not {"ck_vip_reward_notice_status", "ck_vip_reward_notice_attempts"}.issubset(checks)
                or not any(key["constrained_columns"] == ["grant_id"]
                           and key["referred_table"] == "vip_reward_grant"
                           and key["referred_columns"] == ["id"]
                           and key.get("options", {}).get("ondelete", "").upper() == "CASCADE"
                           for key in foreign_keys)):
            raise RuntimeError("Unexpected staged VIP reward notice schema")
        return
    op.create_table(
        "vip_reward_notice",
        sa.Column("grant_id", sa.Integer(), sa.ForeignKey("vip_reward_grant.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("server_number", sa.Integer(), nullable=False),
        sa.Column("player_id", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("due_at", sa.Float(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.CheckConstraint("status IN ('queued', 'sending', 'sent', 'review', 'failed', 'expired')", name="ck_vip_reward_notice_status"),
        sa.CheckConstraint("attempts >= 0", name="ck_vip_reward_notice_attempts"),
    )
    op.create_index("ix_vip_reward_notice_server_number", "vip_reward_notice", ["server_number"])
    op.create_index("ix_vip_reward_notice_status", "vip_reward_notice", ["status"])


def downgrade():
    pending = op.get_bind().execute(sa.text(
        "SELECT count(*) FROM vip_reward_notice WHERE status IN ('queued', 'sending', 'review')"
    )).scalar_one()
    if pending:
        raise RuntimeError("Resolve or archive pending VIP notices before downgrade")
    op.drop_index("ix_vip_reward_notice_status", table_name="vip_reward_notice")
    op.drop_index("ix_vip_reward_notice_server_number", table_name="vip_reward_notice")
    op.drop_table("vip_reward_notice")
