"""create problems

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "problems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(120), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("difficulty", sa.String(10), nullable=False),
        sa.Column("topic", sa.String(50), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
    )
    op.create_index("ix_problems_slug", "problems", ["slug"], unique=True)
    op.create_index("ix_problems_topic", "problems", ["topic"])


def downgrade() -> None:
    op.drop_index("ix_problems_topic", table_name="problems")
    op.drop_index("ix_problems_slug", table_name="problems")
    op.drop_table("problems")