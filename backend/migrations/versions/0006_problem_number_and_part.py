"""add question number and part to problems

Revision ID: 0006
Revises: 0005
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("problems", sa.Column("number", sa.Integer(), nullable=True))
    op.add_column("problems", sa.Column("part", sa.String(100), nullable=True))
    op.create_index("ix_problems_number", "problems", ["number"], unique=True)
    # Several questions share one LeetCode page, so the slug can no longer be unique.
    op.drop_index("ix_problems_slug", table_name="problems")
    op.create_index("ix_problems_slug", "problems", ["slug"])


def downgrade() -> None:
    op.drop_index("ix_problems_slug", table_name="problems")
    op.create_index("ix_problems_slug", "problems", ["slug"], unique=True)
    op.drop_index("ix_problems_number", table_name="problems")
    op.drop_column("problems", "part")
    op.drop_column("problems", "number")