"""Import course content from the content folder into the database.

Run from inside the api container:
    python -m app.scripts.import_content [content_root]

The whole tree is validated before anything is written, so a typo in one file
never leaves the database half-updated. Rows are matched by slug, so student
progress (which points at lesson IDs) survives a re-import.
"""
import asyncio
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal, engine
from app.models.learn import Exercise, Lesson, Module, Subject

# backend/content locally, /srv/content inside the container.
DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "content"

SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
HEADER_RE = re.compile(r"\A---\n(.*?)\n---[ \t]*(?:\n|\Z)(.*)\Z", re.DOTALL)
EXERCISE_KINDS = {"local"}


class ContentError(Exception):
    """A content file is invalid. Nothing is written to the database."""


@dataclass
class ExerciseDoc:
    kind: str
    steps: list[dict[str, str]]


@dataclass
class LessonDoc:
    slug: str
    title: str
    position: int
    published: bool
    body: str
    exercise: ExerciseDoc | None


@dataclass
class ModuleDoc:
    slug: str
    title: str
    position: int
    published: bool
    lessons: list[LessonDoc] = field(default_factory=list)


@dataclass
class SubjectDoc:
    slug: str
    title: str
    description: str
    position: int
    published: bool
    modules: list[ModuleDoc] = field(default_factory=list)


# ---------------------------------------------------------------- parsing


def read_document(path: Path) -> tuple[dict[str, Any], str]:
    """Split a content file into its YAML header and its markdown body."""
    # utf-8-sig drops the BOM that some Windows editors add.
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    match = HEADER_RE.match(text)
    if match is None:
        raise ContentError(f"{path}: the file must start with a '---' header block.")
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ContentError(f"{path}: invalid header ({exc}).") from None
    if not isinstance(meta, dict):
        raise ContentError(f"{path}: the header must contain key: value pairs.")
    return meta, match.group(2).strip()


def _text(meta: dict[str, Any], key: str, path: Path, max_len: int) -> str:
    value = meta.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContentError(f"{path}: '{key}' is required.")
    value = value.strip()
    if len(value) > max_len:
        raise ContentError(f"{path}: '{key}' is longer than {max_len} characters.")
    return value


def _slug(meta: dict[str, Any], path: Path) -> str:
    slug = _text(meta, "slug", path, 100)
    if not SLUG_RE.fullmatch(slug):
        raise ContentError(
            f"{path}: slug '{slug}' may only use lowercase letters, digits and hyphens."
        )
    return slug


def _position(meta: dict[str, Any], path: Path) -> int:
    value = meta.get("position")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ContentError(f"{path}: 'position' must be a whole number, 0 or more.")
    return value


def _published(meta: dict[str, Any], path: Path) -> bool:
    value = meta.get("published", False)
    if not isinstance(value, bool):
        raise ContentError(f"{path}: 'published' must be true or false.")
    return value


def _step_field(
    step: dict[str, Any], key: str, path: Path, number: int, *, required: bool = False
) -> str:
    value = step.get(key)
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ContentError(f"{path}: step {number}: '{key}' must be text.")
    value = value.strip()
    if required and not value:
        raise ContentError(f"{path}: step {number}: '{key}' is required.")
    return value


def _parse_exercise(meta: dict[str, Any], path: Path) -> ExerciseDoc | None:
    raw = meta.get("exercise")
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ContentError(f"{path}: 'exercise' must contain kind and steps.")
    kind = raw.get("kind", "local")
    if kind not in EXERCISE_KINDS:
        allowed = ", ".join(sorted(EXERCISE_KINDS))
        raise ContentError(f"{path}: exercise kind must be one of: {allowed}.")
    raw_steps = raw.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ContentError(f"{path}: an exercise needs at least one step.")

    steps: list[dict[str, str]] = []
    for number, step in enumerate(raw_steps, start=1):
        if not isinstance(step, dict):
            raise ContentError(f"{path}: step {number} must be key: value pairs.")
        steps.append(
            {
                "instruction": _step_field(
                    step, "instruction", path, number, required=True
                ),
                "command": _step_field(step, "command", path, number),
                "expected_output": _step_field(step, "expected_output", path, number),
                "check": _step_field(step, "check", path, number),
            }
        )
    return ExerciseDoc(kind=kind, steps=steps)


def _ensure_unique(values: list[str], what: str, where: Path) -> None:
    duplicates = sorted(v for v, count in Counter(values).items() if count > 1)
    if duplicates:
        raise ContentError(f"{where}: duplicate {what} slug(s): {', '.join(duplicates)}.")


def _content_dirs(parent: Path) -> list[Path]:
    # Folders starting with "_" or "." are ignored, handy for notes and drafts.
    return sorted(
        p for p in parent.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))
    )


def _require_file(path: Path) -> Path:
    if not path.is_file():
        raise ContentError(f"Missing file: {path}")
    return path


def _load_lesson(path: Path) -> LessonDoc:
    meta, body = read_document(path)
    if not body:
        raise ContentError(f"{path}: the lecture text is empty.")
    return LessonDoc(
        slug=_slug(meta, path),
        title=_text(meta, "title", path, 200),
        position=_position(meta, path),
        published=_published(meta, path),
        body=body,
        exercise=_parse_exercise(meta, path),
    )


def _load_module(module_dir: Path) -> ModuleDoc:
    module_file = _require_file(module_dir / "module.md")
    meta, _ = read_document(module_file)
    module = ModuleDoc(
        slug=_slug(meta, module_file),
        title=_text(meta, "title", module_file, 200),
        position=_position(meta, module_file),
        published=_published(meta, module_file),
    )
    for lesson_file in sorted(module_dir.glob("*.md")):
        if lesson_file.name == "module.md" or lesson_file.name.startswith(("_", ".")):
            continue
        module.lessons.append(_load_lesson(lesson_file))
    return module


def _load_subject(subject_dir: Path) -> SubjectDoc:
    subject_file = _require_file(subject_dir / "subject.md")
    meta, description = read_document(subject_file)
    subject = SubjectDoc(
        slug=_slug(meta, subject_file),
        title=_text(meta, "title", subject_file, 200),
        description=description,
        position=_position(meta, subject_file),
        published=_published(meta, subject_file),
    )
    for module_dir in _content_dirs(subject_dir):
        subject.modules.append(_load_module(module_dir))
    _ensure_unique([m.slug for m in subject.modules], "module", subject_dir)
    _ensure_unique(
        [lesson.slug for m in subject.modules for lesson in m.lessons],
        "lesson",
        subject_dir,
    )
    return subject


def load_content(root: Path) -> list[SubjectDoc]:
    learn_dir = root / "learn"
    if not learn_dir.is_dir():
        raise ContentError(f"Content folder not found: {learn_dir}")
    subjects = [_load_subject(d) for d in _content_dirs(learn_dir)]
    _ensure_unique([s.slug for s in subjects], "subject", learn_dir)
    return subjects


# ---------------------------------------------------------------- syncing


def _apply(
    session: AsyncSession,
    model: type,
    row: Any,
    fields: dict[str, Any],
    stats: Counter[str],
    label: str,
) -> Any:
    if row is None:
        row = model(**fields)
        session.add(row)
        stats[f"{label} created"] += 1
        return row
    changed = False
    for name, value in fields.items():
        if getattr(row, name) != value:
            setattr(row, name, value)
            changed = True
    if changed:
        stats[f"{label} updated"] += 1
    return row


async def sync(session: AsyncSession, subjects: list[SubjectDoc]) -> Counter[str]:
    stats: Counter[str] = Counter()

    subject_rows = {row.slug: row for row in await session.scalars(select(Subject))}
    module_rows = {
        (row.subject_id, row.slug): row for row in await session.scalars(select(Module))
    }
    lesson_rows = {
        (row.subject_id, row.slug): row for row in await session.scalars(select(Lesson))
    }
    exercise_rows = {
        row.lesson_id: row for row in await session.scalars(select(Exercise))
    }
    seen_subjects: set[int] = set()
    seen_modules: set[int] = set()
    seen_lessons: set[int] = set()

    for sd in subjects:
        subject = _apply(
            session,
            Subject,
            subject_rows.get(sd.slug),
            {
                "slug": sd.slug,
                "title": sd.title,
                "description": sd.description,
                "position": sd.position,
                "is_published": sd.published,
            },
            stats,
            "subjects",
        )
        await session.flush()  # new rows need their ID for the children below
        seen_subjects.add(subject.id)

        for md in sd.modules:
            module = _apply(
                session,
                Module,
                module_rows.get((subject.id, md.slug)),
                {
                    "subject_id": subject.id,
                    "slug": md.slug,
                    "title": md.title,
                    "position": md.position,
                    "is_published": md.published,
                },
                stats,
                "modules",
            )
            await session.flush()
            seen_modules.add(module.id)

            for ld in md.lessons:
                lesson = _apply(
                    session,
                    Lesson,
                    lesson_rows.get((subject.id, ld.slug)),
                    {
                        "subject_id": subject.id,
                        "module_id": module.id,
                        "slug": ld.slug,
                        "title": ld.title,
                        "body": ld.body,
                        "position": ld.position,
                        "is_published": ld.published,
                    },
                    stats,
                    "lessons",
                )
                await session.flush()
                seen_lessons.add(lesson.id)

                exercise = exercise_rows.get(lesson.id)
                if ld.exercise is None:
                    if exercise is not None:
                        await session.delete(exercise)
                        stats["exercises removed"] += 1
                else:
                    _apply(
                        session,
                        Exercise,
                        exercise,
                        {
                            "lesson_id": lesson.id,
                            "kind": ld.exercise.kind,
                            "steps": ld.exercise.steps,
                        },
                        stats,
                        "exercises",
                    )

    # Content that disappeared from the files is hidden, never deleted,
    # so student progress is kept.
    for rows, seen, label in (
        (subject_rows.values(), seen_subjects, "subjects"),
        (module_rows.values(), seen_modules, "modules"),
        (lesson_rows.values(), seen_lessons, "lessons"),
    ):
        for row in rows:
            if row.id not in seen and row.is_published:
                row.is_published = False
                stats[f"{label} unpublished"] += 1

    return stats


async def import_content(
    session: AsyncSession, root: Path = DEFAULT_ROOT
) -> Counter[str]:
    subjects = load_content(root)  # raises ContentError before any write
    stats = await sync(session, subjects)
    await session.commit()
    return stats


async def main(root: Path) -> None:
    async with SessionLocal() as session:
        stats = await import_content(session, root)
    await engine.dispose()
    if not stats:
        print("Nothing changed.")
    for name, count in sorted(stats.items()):
        print(f"{name}: {count}")


if __name__ == "__main__":
    content_root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ROOT
    try:
        asyncio.run(main(content_root))
    except ContentError as exc:
        print(f"Content error: {exc}")
        raise SystemExit(1) from None