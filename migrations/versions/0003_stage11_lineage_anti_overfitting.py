"""stage 11 lineage and anti-overfitting controls

Revision ID: 0003_stage11
Revises: 0002_stage6
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_stage11"
down_revision = "0002_stage6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "experiments",
        sa.Column("parent_experiment_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "experiments",
        sa.Column("generation", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "experiments",
        sa.Column("dataset_fingerprint", sa.String(64), nullable=True),
    )
    op.add_column(
        "experiments",
        sa.Column("lineage_fingerprint", sa.String(64), nullable=True),
    )
    op.create_foreign_key(
        "fk_experiments_parent_experiment",
        "experiments",
        "experiments",
        ["parent_experiment_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_experiments_parent_experiment_id",
        "experiments",
        ["parent_experiment_id"],
    )
    op.create_unique_constraint(
        "uq_experiments_lineage_fingerprint",
        "experiments",
        ["lineage_fingerprint"],
    )
    op.alter_column("experiments", "generation", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "uq_experiments_lineage_fingerprint", "experiments", type_="unique"
    )
    op.drop_index("ix_experiments_parent_experiment_id", table_name="experiments")
    op.drop_constraint(
        "fk_experiments_parent_experiment", "experiments", type_="foreignkey"
    )
    op.drop_column("experiments", "lineage_fingerprint")
    op.drop_column("experiments", "dataset_fingerprint")
    op.drop_column("experiments", "generation")
    op.drop_column("experiments", "parent_experiment_id")
