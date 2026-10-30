import asyncio
import re
from collections.abc import Iterator
from typing import NamedTuple
from urllib.parse import quote_plus

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal, engine
from app.models.problem import Problem
from app.scripts.dsa_questions import PARTS


class Question(NamedTuple):
    part: str
    section: str
    number: int
    title: str
    leetcode_slug: str | None
    difficulty: str


def iter_questions() -> Iterator[Question]:
    for part, sections in PARTS:
        for section, items in sections:
            for number, title, leetcode_slug, difficulty in items:
                yield Question(part, section, number, title, leetcode_slug, difficulty)


def build_url(title: str, leetcode_slug: str | None) -> str:
    if leetcode_slug:
        return f"https://leetcode.com/problems/{leetcode_slug}/"
    # No direct page known: search GeeksforGeeks for the question instead.
    return "https://www.google.com/search?q=" + quote_plus(f"{title} geeksforgeeks")


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:120]


async def seed(session: AsyncSession) -> dict[str, int]:
    stats = {"created": 0, "updated": 0, "adopted": 0, "removed": 0}

    numbered = {
        p.number: p
        for p in await session.scalars(select(Problem).where(Problem.number.is_not(None)))
    }
    # Rows from the first starter set. Matching ones are adopted so solve history is kept.
    legacy = {
        p.slug: p
        for p in await session.scalars(select(Problem).where(Problem.number.is_(None)))
    }

    for q in iter_questions():
        fields = {
            "number": q.number,
            "slug": q.leetcode_slug or slugify(q.title),
            "title": q.title,
            "difficulty": q.difficulty,
            "topic": q.section,
            "part": q.part,
            "url": build_url(q.title, q.leetcode_slug),
        }
        problem = numbered.get(q.number)
        if problem is not None:
            stats["updated"] += 1
        elif q.leetcode_slug and q.leetcode_slug in legacy:
            problem = legacy.pop(q.leetcode_slug)
            stats["adopted"] += 1

        if problem is None:
            session.add(Problem(**fields))
            stats["created"] += 1
        else:
            for name, value in fields.items():
                setattr(problem, name, value)

    # Old starter questions that are not in the new list.
    for leftover in legacy.values():
        await session.delete(leftover)
        stats["removed"] += 1

    await session.commit()
    return stats


async def main() -> None:
    async with SessionLocal() as session:
        stats = await seed(session)
    await engine.dispose()
    print(
        "Created {created}, updated {updated}, adopted {adopted} old, "
        "removed {removed} old.".format(**stats)
    )


if __name__ == "__main__":
    asyncio.run(main())