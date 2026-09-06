"""stage 6 experiment management

Revision ID: 0002_stage6
Revises: 0001_stage2
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_stage6"
down_revision = "0001_stage2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column("experiment_fingerprint", sa.String(64), nullable=True),
    )
    op.add_column(
        "experiments",
        sa.Column("engine_version", sa.String(50), nullable=True),
    )
    op.create_unique_constraint(
        "uq_experiments_experiment_fingerprint",
        "experiments",
        ["experiment_fingerprint"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_experiments_experiment_fingerprint", "experiments", type_="unique"
    )
    op.drop_column("experiments", "engine_version")
    op.drop_column("experiments", "experiment_fingerprint")
