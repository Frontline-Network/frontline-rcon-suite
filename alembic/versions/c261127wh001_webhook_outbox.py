"""Durable webhook payloads and serialized per-queue admission."""
import sqlalchemy as sa
from alembic import op

revision = "c261127wh001"
down_revision = "v261119voice02"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "webhook_outbox_queue",
        sa.Column("queue_hash", sa.String(64), primary_key=True),
        sa.Column("queue_id", sa.Text(), nullable=False),
        sa.Column("native_snapshot_seen", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("legacy_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("legacy_review_generation", sa.String(32)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_table(
        "webhook_outbox_delivery",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True),
        sa.Column("message_id", sa.String(64), nullable=False),
        sa.Column("dedupe_key", sa.String(192)),
        sa.Column("queue_hash", sa.String(64), sa.ForeignKey("webhook_outbox_queue.queue_hash"), nullable=False),
        sa.Column("server_number", sa.Integer()),
        sa.Column("webhook_type", sa.String(64)),
        sa.Column("message_type", sa.String(128)),
        sa.Column("payload", sa.LargeBinary()),
        sa.Column("payload_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("source_acknowledged", sa.Boolean(), nullable=False),
        sa.Column("operator_retry", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("owner_token", sa.String(32)),
        sa.Column("lease_until", sa.TIMESTAMP(timezone=True)),
        sa.Column("available_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("reason", sa.String(80)),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True)),
        sa.UniqueConstraint("message_id", name="uq_webhook_outbox_message"),
        sa.UniqueConstraint("dedupe_key", name="uq_webhook_outbox_dedupe"),
        sa.CheckConstraint("status IN ('queued','claimed','sending','sent','review','superseded')", name="ck_webhook_outbox_status"),
        sa.CheckConstraint("priority IN (0,1)", name="ck_webhook_outbox_priority"),
        sa.CheckConstraint("attempts >= 0", name="ck_webhook_outbox_attempts"),
        sa.CheckConstraint("server_number IS NULL OR server_number BETWEEN 1 AND 2147483647", name="ck_webhook_outbox_server"),
        sa.CheckConstraint("status IN ('sent','superseded') OR payload IS NOT NULL", name="ck_webhook_outbox_payload"),
    )
    op.create_index("ix_webhook_outbox_queue_order", "webhook_outbox_delivery", ["queue_hash", "priority", "id"])
    op.create_index("ix_webhook_outbox_pending", "webhook_outbox_delivery", ["status", "available_at", "id"])
    op.create_index("ix_webhook_outbox_lease", "webhook_outbox_delivery", ["status", "lease_until"])
    op.create_index("ix_webhook_outbox_completed", "webhook_outbox_delivery", ["status", "completed_at", "id"])


def downgrade():
    # A downgrade must never silently discard accepted or reviewable payloads.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Fence producers for the entire check/drop transaction. Otherwise a
        # message could commit between an empty COUNT and the subsequent DDL.
        op.execute("LOCK TABLE webhook_outbox_queue, webhook_outbox_delivery IN ACCESS EXCLUSIVE MODE")
    elif bind.dialect.name == "sqlite":
        raw_connection = bind.connection.dbapi_connection
        if not raw_connection.in_transaction:
            bind.exec_driver_sql("BEGIN IMMEDIATE")
    count = bind.execute(sa.text("SELECT count(*) FROM webhook_outbox_delivery "
        "WHERE payload IS NOT NULL OR source_acknowledged = false")).scalar()
    if count:
        raise RuntimeError("Resolve or export retained webhook payloads before downgrading")
    op.drop_table("webhook_outbox_delivery")
    op.drop_table("webhook_outbox_queue")
