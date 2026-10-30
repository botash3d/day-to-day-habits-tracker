"""add attempt duration

Revision ID: 0004
Revises: 0003
"""
import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "attempts", sa.Column("duration_seconds", sa.Integer(), nullable=True)
    )
    op.execute(
        "UPDATE attempts SET duration_seconds = "
        "CAST(EXTRACT(EPOCH FROM (finished_at - started_at)) AS INTEGER) "
        "WHERE finished_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("attempts", "duration_seconds")