from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Position in the curated list (1-250). Rows without a number are unsorted extras.
    number: Mapped[int | None] = mapped_column(unique=True, index=True, default=None)
    # Not unique: a few questions share one LeetCode page.
    slug: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(200))
    difficulty: Mapped[str] = mapped_column(String(10))
    # The section (subheading), e.g. "Sliding Window".
    topic: Mapped[str] = mapped_column(String(50), index=True)
    # The part (heading), e.g. "Part 1: Questions 1-50".
    part: Mapped[str | None] = mapped_column(String(100), default=None)
    url: Mapped[str] = mapped_column(String(500))