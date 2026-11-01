from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.learn import Exercise, Lesson, LessonProgress, Subject
from app.models.user import User
from app.scripts.import_content import (
    DEFAULT_ROOT,
    ContentError,
    import_content,
    load_content,
)

pytestmark = pytest.mark.asyncio

SUBJECT = "slug: demo\ntitle: Demo\nposition: 1\npublished: true"
MODULE = "slug: intro\ntitle: Intro\nposition: 1\npublished: true"
LESSON_ONE = """slug: one
title: One
position: 1
published: true
exercise:
  kind: local
  steps:
    - instruction: Do it
      command: echo hi
      expected_output: hi
      check: You see hi"""
LESSON_TWO = "slug: two\ntitle: Two\nposition: 2\npublished: true"
VALID_LESSON = "slug: extra\ntitle: Extra\nposition: 3\npublished: true"

LESSON_ONE_FILE = "learn/demo/01-intro/01-one.md"
LESSON_TWO_FILE = "learn/demo/01-intro/02-two.md"
EXTRA_FILE = "learn/demo/01-intro/03-extra.md"


def write(root: Path, relative: str, header: str, body: str = "") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{header.strip()}\n---\n{body}\n", encoding="utf-8")


def make_course(root: Path) -> None:
    write(root, "learn/demo/subject.md", SUBJECT, "A demo subject.")
    write(root, "learn/demo/01-intro/module.md", MODULE)
    write(root, LESSON_ONE_FILE, LESSON_ONE, "Lecture one.")
    write(root, LESSON_TWO_FILE, LESSON_TWO, "Lecture two.")


async def count(session, model) -> int:
    return len((await session.scalars(select(model))).all())


async def test_first_import_creates_everything(tmp_path, session_factory):
    make_course(tmp_path)

    async with session_factory() as session:
        stats = await import_content(session, tmp_path)

        assert dict(stats) == {
            "subjects created": 1,
            "modules created": 1,
            "lessons created": 2,
            "exercises created": 1,
        }
        subject = await session.scalar(select(Subject))
        assert subject.slug == "demo"
        assert subject.description == "A demo subject."
        assert subject.is_published is True
        one = await session.scalar(select(Lesson).where(Lesson.slug == "one"))
        assert one.body == "Lecture one."
        exercise = await session.scalar(select(Exercise))
        assert exercise.lesson_id == one.id
        assert exercise.steps == [
            {
                "instruction": "Do it",
                "command": "echo hi",
                "expected_output": "hi",
                "check": "You see hi",
            }
        ]


async def test_reimport_changes_nothing_and_keeps_ids(tmp_path, session_factory):
    make_course(tmp_path)
    async with session_factory() as session:
        await import_content(session, tmp_path)
        ids_before = {
            row.slug: row.id for row in (await session.scalars(select(Lesson))).all()
        }

    async with session_factory() as session:
        stats = await import_content(session, tmp_path)
        ids_after = {
            row.slug: row.id for row in (await session.scalars(select(Lesson))).all()
        }

    assert not stats
    assert ids_after == ids_before


async def test_edited_lesson_is_updated_in_place(tmp_path, session_factory):
    make_course(tmp_path)
    async with session_factory() as session:
        await import_content(session, tmp_path)

    write(tmp_path, LESSON_TWO_FILE, LESSON_TWO, "A better lecture two.")
    async with session_factory() as session:
        stats = await import_content(session, tmp_path)
        two = await session.scalar(select(Lesson).where(Lesson.slug == "two"))

    assert dict(stats) == {"lessons updated": 1}
    assert two.body == "A better lecture two."


LESSON_ONE_NO_EXERCISE = "slug: one\ntitle: One\nposition: 1\npublished: true"


async def test_removed_exercise_is_deleted(tmp_path, session_factory):
    make_course(tmp_path)
    async with session_factory() as session:
        await import_content(session, tmp_path)

    write(tmp_path, LESSON_ONE_FILE, LESSON_ONE_NO_EXERCISE, "Lecture one.")
    async with session_factory() as session:
        stats = await import_content(session, tmp_path)
        remaining = await count(session, Exercise)

    assert stats["exercises removed"] == 1
    assert remaining == 0


async def test_removed_lesson_is_unpublished_and_progress_is_kept(
    tmp_path, session_factory
):
    make_course(tmp_path)
    async with session_factory() as session:
        await import_content(session, tmp_path)
        user = User(email="a@example.com", full_name="A", hashed_password="x")
        session.add(user)
        await session.flush()
        two = await session.scalar(select(Lesson).where(Lesson.slug == "two"))
        session.add(
            LessonProgress(
                user_id=user.id, lesson_id=two.id, completed_at=datetime.now(UTC)
            )
        )
        await session.commit()

    (tmp_path / LESSON_TWO_FILE).unlink()
    async with session_factory() as session:
        stats = await import_content(session, tmp_path)
        two = await session.scalar(select(Lesson).where(Lesson.slug == "two"))
        progress_rows = await count(session, LessonProgress)

    assert dict(stats) == {"lessons unpublished": 1}
    assert two is not None
    assert two.is_published is False
    assert progress_rows == 1


async def test_invalid_content_writes_nothing(tmp_path, session_factory):
    make_course(tmp_path)
    write(tmp_path, "learn/zzz/subject.md",
          "slug: Bad Slug\ntitle: Bad\nposition: 2\npublished: true")
    write(tmp_path, "learn/zzz/01-m/module.md", MODULE)

    async with session_factory() as session:
        with pytest.raises(ContentError, match="slug"):
            await import_content(session, tmp_path)
        # The valid "demo" subject must not have been imported either.
        assert await count(session, Subject) == 0
        assert await count(session, Lesson) == 0


@pytest.mark.parametrize(
    ("header", "body", "message"),
    [
        ("slug: Bad Slug\ntitle: T\nposition: 3\npublished: true", "Body.", "slug"),
        ("slug: bad\nposition: 3\npublished: true", "Body.", "title"),
        ("slug: bad\ntitle: T\nposition: three\npublished: true", "Body.", "position"),
        ("slug: bad\ntitle: T\nposition: 3\npublished: yes please", "Body.", "published"),
        ("slug: bad\ntitle: T\nposition: 3\npublished: true", "", "empty"),
        (
            "slug: bad\ntitle: T\nposition: 3\npublished: true\n"
            "exercise:\n  kind: video\n  steps: []",
            "Body.",
            "kind",
        ),
        (
            "slug: bad\ntitle: T\nposition: 3\npublished: true\n"
            "exercise:\n  kind: local\n  steps: []",
            "Body.",
            "at least one step",
        ),
        (
            "slug: bad\ntitle: T\nposition: 3\npublished: true\n"
            "exercise:\n  steps:\n    - command: ls",
            "Body.",
            "instruction",
        ),
    ],
)
async def test_invalid_lesson_files_are_rejected(tmp_path, header, body, message):
    make_course(tmp_path)
    write(tmp_path, EXTRA_FILE, header, body)

    with pytest.raises(ContentError, match=message):
        load_content(tmp_path)


async def test_file_without_header_is_rejected(tmp_path):
    make_course(tmp_path)
    (tmp_path / EXTRA_FILE).write_text("Just text, no header.", encoding="utf-8")

    with pytest.raises(ContentError, match="header"):
        load_content(tmp_path)


async def test_duplicate_lesson_slug_in_a_subject_is_rejected(tmp_path):
    make_course(tmp_path)
    write(tmp_path, "learn/demo/02-other/module.md",
          "slug: other\ntitle: Other\nposition: 2\npublished: true")
    write(tmp_path, "learn/demo/02-other/01-one.md",
          "slug: one\ntitle: Again\nposition: 1\npublished: true", "Body.")

    with pytest.raises(ContentError, match="duplicate lesson"):
        load_content(tmp_path)


async def test_module_folder_without_module_file_is_rejected(tmp_path):
    make_course(tmp_path)
    write(tmp_path, "learn/demo/02-other/01-lesson.md", VALID_LESSON, "Body.")

    with pytest.raises(ContentError, match="Missing file"):
        load_content(tmp_path)


async def test_underscore_folders_and_files_are_ignored(tmp_path):
    make_course(tmp_path)
    (tmp_path / "learn/demo/_notes").mkdir()
    (tmp_path / "learn/demo/_notes/ideas.md").write_text("no header", encoding="utf-8")
    (tmp_path / "learn/demo/01-intro/_draft.md").write_text("no header", encoding="utf-8")

    subjects = load_content(tmp_path)

    assert [len(m.lessons) for m in subjects[0].modules] == [2]


async def test_windows_line_endings_and_bom_are_handled(tmp_path):
    make_course(tmp_path)
    text = (
        "---\r\nslug: one\r\ntitle: One\r\nposition: 1\r\npublished: true\r\n---\r\n"
        "Lecture.\r\n"
    )
    (tmp_path / LESSON_ONE_FILE).write_bytes(text.encode("utf-8-sig"))  # adds a BOM

    subjects = load_content(tmp_path)

    lesson = subjects[0].modules[0].lessons[0]
    assert lesson.slug == "one"
    assert lesson.body == "Lecture."


async def test_missing_content_folder_is_reported(tmp_path):
    with pytest.raises(ContentError, match="not found"):
        load_content(tmp_path)


async def test_bundled_course_content_is_valid():
    subjects = load_content(DEFAULT_ROOT)

    assert subjects
    for subject in subjects:
        for module in subject.modules:
            for lesson in module.lessons:
                assert lesson.body