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


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    # Drafts stay hidden until the content file says "published: true".
    is_published: Mapped[bool] = mapped_column(
        default=False, server_default=sa.false()
    )


class Module(Base):
    __tablename__ = "modules"
    __table_args__ = (
        UniqueConstraint("subject_id", "slug", name="uq_modules_subject_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    is_published: Mapped[bool] = mapped_column(
        default=False, server_default=sa.false()
    )


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (
        # The URL is /learn/:subject/:lesson, so a slug is unique per subject.
        UniqueConstraint("subject_id", "slug", name="uq_lessons_subject_slug"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), index=True
    )
    module_id: Mapped[int] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), index=True
    )
    slug: Mapped[str] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200))
    # The lecture, as markdown (code examples are fenced blocks inside it).
    body: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(default=0, server_default="0")
    is_published: Mapped[bool] = mapped_column(
        default=False, server_default=sa.false()
    )


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(primary_key=True)
    # One exercise per lesson for now.
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), unique=True, index=True
    )
    # "local" = students run the steps on their own machine.
    kind: Mapped[str] = mapped_column(String(20), default="local", server_default="local")
    # Ordered list of {instruction, command, expected_output, check}.
    steps: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list)


class LessonProgress(Base):
    __tablename__ = "lesson_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    lesson_id: Mapped[int] = mapped_column(
        ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )