from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.models.build import Project, ProjectModule, ProjectPage, ProjectPageProgress
from app.models.learn import Subject
from app.models.user import User
from app.scripts.import_all import import_everything, summarize
from app.scripts.import_build import load_build_content, sync_build
from app.scripts.import_content import DEFAULT_ROOT, ContentError

pytestmark = pytest.mark.asyncio

PROJECT = "slug: shortener\ntitle: URL Shortener\nposition: 1\npublished: true"
MODULE = "slug: setup\ntitle: Setup\nposition: 1\npublished: true"
GOAL = "slug: goal\ntitle: Goal\nkind: explain\nposition: 1\npublished: true"
STUCK = (
    "slug: stuck\ntitle: Stuck?\nkind: stuck\nposition: 2\npublished: true\n"
    "hints:\n  - First hint.\n  - Second hint."
)
EXTRA = "slug: extra\ntitle: Extra\nkind: explain\nposition: 3\npublished: true"

BASE = "build/shortener/01-setup"
GOAL_FILE = f"{BASE}/01-goal.md"
STUCK_FILE = f"{BASE}/02-stuck.md"
EXTRA_FILE = f"{BASE}/03-extra.md"


def write(root: Path, relative: str, header: str, body: str = "") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{header.strip()}\n---\n{body}\n", encoding="utf-8")


def make_project(root: Path) -> None:
    write(root, "build/shortener/project.md", PROJECT, "A demo project.")
    write(root, f"{BASE}/module.md", MODULE, "Module summary.")
    write(root, GOAL_FILE, GOAL, "Goal text.")
    write(root, STUCK_FILE, STUCK, "Stuck text.")
    checkpoint = root / BASE / "checkpoint"
    (checkpoint / "tests").mkdir(parents=True)
    (checkpoint / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (checkpoint / "tests" / "test_x.py").write_text(
        "def test_x():\n    pass\n", encoding="utf-8"
    )


def make_learn(root: Path) -> None:
    write(
        root,
        "learn/demo/subject.md",
        "slug: demo\ntitle: Demo\nposition: 1\npublished: true",
        "A demo subject.",
    )
    write(
        root,
        "learn/demo/01-intro/module.md",
        "slug: intro\ntitle: Intro\nposition: 1\npublished: true",
    )
    write(
        root,
        "learn/demo/01-intro/01-one.md",
        "slug: one\ntitle: One\nposition: 1\npublished: true",
        "Lecture.",
    )


async def import_build(session, root: Path):
    stats = await sync_build(session, load_build_content(root))
    await session.commit()
    return stats


async def count(session, model) -> int:
    return len((await session.scalars(select(model))).all())


async def test_first_import_creates_everything(tmp_path, session_factory):
    make_project(tmp_path)

    async with session_factory() as session:
        stats = await import_build(session, tmp_path)

        assert dict(stats) == {
            "projects created": 1,
            "project modules created": 1,
            "project pages created": 2,
        }
        project = await session.scalar(select(Project))
        assert project.slug == "shortener"
        assert project.description == "A demo project."
        assert project.is_published is True
        module = await session.scalar(select(ProjectModule))
        assert module.summary == "Module summary."
        assert module.checkpoint == [
            {"path": "main.py", "content": "print('hello')\n"},
            {"path": "tests/test_x.py", "content": "def test_x():\n    pass\n"},
        ]
        stuck = await session.scalar(select(ProjectPage).where(ProjectPage.slug == "stuck"))
        assert stuck.kind == "stuck"
        assert stuck.hints == ["First hint.", "Second hint."]
        assert stuck.body == "Stuck text."
        goal = await session.scalar(select(ProjectPage).where(ProjectPage.slug == "goal"))
        assert goal.hints == []


async def test_reimport_changes_nothing_and_keeps_ids(tmp_path, session_factory):
    make_project(tmp_path)
    async with session_factory() as session:
        await import_build(session, tmp_path)
        ids_before = {
            row.slug: row.id for row in (await session.scalars(select(ProjectPage))).all()
        }

    async with session_factory() as session:
        stats = await import_build(session, tmp_path)
        ids_after = {
            row.slug: row.id for row in (await session.scalars(select(ProjectPage))).all()
        }

    assert not stats
    assert ids_after == ids_before


async def test_edited_page_is_updated_in_place(tmp_path, session_factory):
    make_project(tmp_path)
    async with session_factory() as session:
        await import_build(session, tmp_path)

    write(tmp_path, GOAL_FILE, GOAL, "A better goal text.")
    async with session_factory() as session:
        stats = await import_build(session, tmp_path)
        goal = await session.scalar(select(ProjectPage).where(ProjectPage.slug == "goal"))

    assert dict(stats) == {"project pages updated": 1}
    assert goal.body == "A better goal text."


async def test_changed_checkpoint_updates_the_module(tmp_path, session_factory):
    make_project(tmp_path)
    async with session_factory() as session:
        await import_build(session, tmp_path)

    (tmp_path / BASE / "checkpoint" / "main.py").write_text("print('v2')\n", encoding="utf-8")
    async with session_factory() as session:
        stats = await import_build(session, tmp_path)
        module = await session.scalar(select(ProjectModule))

    assert dict(stats) == {"project modules updated": 1}
    assert module.checkpoint[0]["content"] == "print('v2')\n"


async def test_removed_page_is_unpublished_and_progress_is_kept(tmp_path, session_factory):
    make_project(tmp_path)
    async with session_factory() as session:
        await import_build(session, tmp_path)
        user = User(email="a@example.com", full_name="A", hashed_password="x")
        session.add(user)
        await session.flush()
        stuck = await session.scalar(select(ProjectPage).where(ProjectPage.slug == "stuck"))
        session.add(
            ProjectPageProgress(
                user_id=user.id, page_id=stuck.id, completed_at=datetime.now(UTC)
            )
        )
        await session.commit()

    (tmp_path / STUCK_FILE).unlink()
    async with session_factory() as session:
        stats = await import_build(session, tmp_path)
        stuck = await session.scalar(select(ProjectPage).where(ProjectPage.slug == "stuck"))
        progress_rows = await count(session, ProjectPageProgress)

    assert dict(stats) == {"project pages unpublished": 1}
    assert stuck is not None
    assert stuck.is_published is False
    assert progress_rows == 1


async def test_page_without_kind_defaults_to_explain(tmp_path):
    make_project(tmp_path)
    write(tmp_path, EXTRA_FILE, "slug: extra\ntitle: Extra\nposition: 3\npublished: true", "Body.")

    projects = load_build_content(tmp_path)

    extra = next(p for p in projects[0].modules[0].pages if p.slug == "extra")
    assert extra.kind == "explain"


@pytest.mark.parametrize(
    ("header", "body", "message"),
    [
        ("slug: bad\ntitle: T\nkind: video\nposition: 3\npublished: true", "Body.", "kind"),
        ("slug: Bad Slug\ntitle: T\nposition: 3\npublished: true", "Body.", "slug"),
        ("slug: bad\nposition: 3\npublished: true", "Body.", "title"),
        ("slug: bad\ntitle: T\nposition: first\npublished: true", "Body.", "position"),
        ("slug: bad\ntitle: T\nposition: 3\npublished: true", "", "empty"),
        (
            "slug: bad\ntitle: T\nposition: 3\npublished: true\nhints: just text",
            "Body.",
            "hints",
        ),
        (
            "slug: bad\ntitle: T\nposition: 3\npublished: true\nhints:\n  - ok\n  - ''",
            "Body.",
            "hints",
        ),
    ],
)
async def test_invalid_pages_are_rejected(tmp_path, header, body, message):
    make_project(tmp_path)
    write(tmp_path, EXTRA_FILE, header, body)

    with pytest.raises(ContentError, match=message):
        load_build_content(tmp_path)


async def test_too_many_hints_are_rejected(tmp_path):
    make_project(tmp_path)
    hints = "".join(f"  - hint {i}\n" for i in range(11))
    write(tmp_path, EXTRA_FILE, f"{EXTRA}\nhints:\n{hints}", "Body.")

    with pytest.raises(ContentError, match="hints"):
        load_build_content(tmp_path)


async def test_duplicate_page_slug_in_a_module_is_rejected(tmp_path):
    make_project(tmp_path)
    write(tmp_path, EXTRA_FILE, GOAL, "Same slug as the first page.")

    with pytest.raises(ContentError, match="duplicate page"):
        load_build_content(tmp_path)


async def test_duplicate_module_slug_in_a_project_is_rejected(tmp_path):
    make_project(tmp_path)
    write(tmp_path, "build/shortener/02-other/module.md", MODULE)

    with pytest.raises(ContentError, match="duplicate module"):
        load_build_content(tmp_path)


async def test_module_folder_without_module_file_is_rejected(tmp_path):
    make_project(tmp_path)
    write(tmp_path, "build/shortener/02-other/01-page.md", EXTRA, "Body.")

    with pytest.raises(ContentError, match="Missing file"):
        load_build_content(tmp_path)


async def test_missing_build_folder_means_no_projects(tmp_path):
    assert load_build_content(tmp_path) == []


async def test_checkpoint_skips_cache_folders_and_compiled_files(tmp_path):
    make_project(tmp_path)
    checkpoint = tmp_path / BASE / "checkpoint"
    (checkpoint / "__pycache__").mkdir()
    (checkpoint / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"\x00\x01")
    (checkpoint / "main.pyc").write_bytes(b"\x00\x01")
    (checkpoint / ".pytest_cache").mkdir()
    (checkpoint / ".pytest_cache" / "README.md").write_text("cache", encoding="utf-8")

    module = load_build_content(tmp_path)[0].modules[0]

    assert [f["path"] for f in module.checkpoint] == ["main.py", "tests/test_x.py"]


async def test_checkpoint_line_endings_are_normalised(tmp_path):
    make_project(tmp_path)
    (tmp_path / BASE / "checkpoint" / "main.py").write_bytes(b"a = 1\r\nb = 2\r\n")

    module = load_build_content(tmp_path)[0].modules[0]

    assert module.checkpoint[0]["content"] == "a = 1\nb = 2\n"


async def test_non_text_checkpoint_file_is_rejected(tmp_path):
    make_project(tmp_path)
    (tmp_path / BASE / "checkpoint" / "main.py").write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(ContentError, match="UTF-8"):
        load_build_content(tmp_path)


async def test_oversized_checkpoint_file_is_rejected(tmp_path):
    make_project(tmp_path)
    (tmp_path / BASE / "checkpoint" / "main.py").write_text("a" * 100_001, encoding="utf-8")

    with pytest.raises(ContentError, match="at most"):
        load_build_content(tmp_path)


async def test_too_many_checkpoint_files_are_rejected(tmp_path):
    make_project(tmp_path)
    for index in range(20):  # plus the two files make_project already created
        extra = tmp_path / BASE / "checkpoint" / f"extra_{index}.py"
        extra.write_text("x = 1\n", encoding="utf-8")
        
    with pytest.raises(ContentError, match="at most 20"):
        load_build_content(tmp_path)


async def test_invalid_build_content_stops_the_whole_import(tmp_path, session_factory):
    make_learn(tmp_path)
    make_project(tmp_path)
    write(tmp_path, EXTRA_FILE, "slug: bad\nposition: 3\npublished: true", "Body.")  # no title

    async with session_factory() as session:
        with pytest.raises(ContentError, match="title"):
            await import_everything(session, tmp_path)
        # The valid Learn content must not have been written either.
        assert await count(session, Subject) == 0
        assert await count(session, Project) == 0


async def test_import_everything_saves_learn_and_build_together(tmp_path, session_factory):
    make_learn(tmp_path)
    make_project(tmp_path)

    async with session_factory() as session:
        stats = await import_everything(session, tmp_path)

    assert stats["subjects created"] == 1
    assert stats["projects created"] == 1
    assert stats["project pages created"] == 2


async def test_summary_describes_the_content(tmp_path):
    make_learn(tmp_path)
    make_project(tmp_path)

    assert summarize(tmp_path) == [
        "Learn (including drafts): 1 subject(s), 1 module(s), 1 lesson(s).",
        "Build (including drafts): 1 project(s), 1 module(s), 2 page(s), "
        "2 checkpoint file(s).",
    ]


async def test_bundled_build_content_is_valid():
    projects = load_build_content(DEFAULT_ROOT)

    assert projects
    for project in projects:
        assert project.modules
        for module in project.modules:
            assert module.pages
            if any(page.kind == "stuck" for page in module.pages):
                assert module.checkpoint
            for page in module.pages:
                assert page.body