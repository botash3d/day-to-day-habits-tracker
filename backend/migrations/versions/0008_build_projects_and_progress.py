"""add build projects, modules, pages and page progress

Revision ID: 0008
Revises: 0007
"""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_published", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_index("ix_projects_slug", "projects", ["slug"], unique=True)

    op.create_table(
        "project_modules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_published", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("checkpoint", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "project_id", "slug", name="uq_project_modules_project_slug"
        ),
    )
    op.create_index("ix_project_modules_project_id", "project_modules", ["project_id"])

    op.create_table(
        "project_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False, server_default="explain"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("hints", sa.JSON(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "is_published", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["module_id"], ["project_modules.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("module_id", "slug", name="uq_project_pages_module_slug"),
    )
    op.create_index("ix_project_pages_project_id", "project_pages", ["project_id"])
    op.create_index("ix_project_pages_module_id", "project_pages", ["module_id"])

    op.create_table(
        "project_page_progress",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("user_id", "page_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_id"], ["project_pages.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_project_page_progress_page_id", "project_page_progress", ["page_id"]
    )


def downgrade() -> None:
    op.drop_table("project_page_progress")
    op.drop_table("project_pages")
    op.drop_table("project_modules")
    op.drop_table("projects")