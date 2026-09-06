"""Stage 20 durable outbox."""

from alembic import op
import sqlalchemy as sa


revision = "0006_stage20"
down_revision = "0005_stage18"
branch_labels = None
depends_on = None


def upgrade() -> None:
    outbox_status = sa.Enum("pending", "published", "failed", name="outbox_status")
    outbox_status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", outbox_status, nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"])
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])
    op.create_index(
        "ix_outbox_events_dispatch",
        "outbox_events",
        ["status", "available_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_events_dispatch", table_name="outbox_events")
    op.drop_index("ix_outbox_events_status", table_name="outbox_events")
    op.drop_index("ix_outbox_events_event_type", table_name="outbox_events")
    op.drop_table("outbox_events")
    sa.Enum("pending", "published", "failed", name="outbox_status").drop(op.get_bind(), checkfirst=True)
