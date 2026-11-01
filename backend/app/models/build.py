import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    is_published: Mapped[bool] = mapped_column(
        default=False, server_default=sa.false()
    )


class ProjectModule(Base):
    __tablename__ = "project_modules"
    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_project_modules_project_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    is_published: Mapped[bool] = mapped_column(
        default=False, server_default=sa.false()
    )
    # The finished code for this module: a list of {path, content}.
    checkpoint: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)


class ProjectPage(Base):
    __tablename__ = "project_pages"
    __table_args__ = (
        # The URL is /build/:project/:module/:page, so a slug is unique per module.
        UniqueConstraint("module_id", "slug", name="uq_project_pages_module_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    module_id: Mapped[int] = mapped_column(
        ForeignKey("project_modules.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    # explain | exercise | run | check | stuck | recap
    kind: Mapped[str] = mapped_column(
        String(20), default="explain", server_default="explain"
    )
    body: Mapped[str] = mapped_column(Text)
    # Revealed one at a time, mainly on "stuck" pages.
    hints: Mapped[list[str]] = mapped_column(JSON, default=list)
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    is_published: Mapped[bool] = mapped_column(
        default=False, server_default=sa.false()
    )


class ProjectPageProgress(Base):
    __tablename__ = "project_page_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    page_id: Mapped[int] = mapped_column(
        ForeignKey("project_pages.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )