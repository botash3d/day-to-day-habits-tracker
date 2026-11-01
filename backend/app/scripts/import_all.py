"""Import all course content (Learn and Build) from the content folder.

    python -m app.scripts.import_all [content_root] [--check]

--check only validates the files and prints a summary; it never touches the
database. Everything is validated before anything is written, and both sections
are saved in one transaction.
"""

import argparse
import asyncio
from collections import Counter
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal, engine
from app.scripts.import_build import load_build_content, sync_build
from app.scripts.import_content import (
    DEFAULT_ROOT,
    ContentError,
    load_content,
    sync,
)


def summarize(root: Path) -> list[str]:
    """Validate the files and describe them. Counts include drafts."""
    subjects = load_content(root)
    projects = load_build_content(root)
    modules = [m for s in subjects for m in s.modules]
    lessons = [lesson for m in modules for lesson in m.lessons]
    project_modules = [m for p in projects for m in p.modules]
    pages = [page for m in project_modules for page in m.pages]
    checkpoint_files = sum(len(m.checkpoint) for m in project_modules)
    return [
        f"Learn (including drafts): {len(subjects)} subject(s), "
        f"{len(modules)} module(s), {len(lessons)} lesson(s).",
        f"Build (including drafts): {len(projects)} project(s), "
        f"{len(project_modules)} module(s), {len(pages)} page(s), "
        f"{checkpoint_files} checkpoint file(s).",
    ]


async def import_everything(
    session: AsyncSession, root: Path = DEFAULT_ROOT
) -> Counter[str]:
    subjects = load_content(root)  # raises ContentError before any write
    projects = load_build_content(root)
    stats = await sync(session, subjects)
    stats.update(await sync_build(session, projects))
    await session.commit()
    return stats


async def run(root: Path) -> None:
    async with SessionLocal() as session:
        stats = await import_everything(session, root)
    await engine.dispose()
    if not stats:
        print("Nothing changed.")
    for name, count in sorted(stats.items()):
        print(f"{name}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Learn and Build content.")
    parser.add_argument("root", nargs="?", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the files only; do not touch the database",
    )
    args = parser.parse_args()
    try:
        if args.check:
            print("\n".join(summarize(args.root)))
            print("Content is valid.")
        else:
            asyncio.run(run(args.root))
    except ContentError as exc:
        print(f"Content error: {exc}")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()