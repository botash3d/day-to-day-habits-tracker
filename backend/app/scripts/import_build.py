"""Import Build projects from the content folder into the database.

Layout, under <content root>/build/:

    <project>/project.md            header + project description
    <project>/<module>/module.md    header + a short summary of the module
    <project>/<module>/<page>.md    header + page text, one file per page
    <project>/<module>/checkpoint/  the finished code for the module (any files)

Like the Learn importer, everything is validated before anything is written, and
rows are matched by slug so student progress survives a re-import. Never move a
page to another module or change its slug casually: progress points at the page.
"""

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.build import Project, ProjectModule, ProjectPage
from app.scripts.import_content import (
    ContentError,
    _apply,
    _content_dirs,
    _ensure_unique,
    _position,
    _published,
    _require_file,
    _slug,
    _text,
    read_document,
)

PAGE_KINDS = ("explain", "exercise", "run", "check", "stuck", "recap")
MAX_HINTS = 10
MAX_HINT_LENGTH = 2000

CHECKPOINT_DIR = "checkpoint"
MAX_CHECKPOINT_FILES = 20
MAX_CHECKPOINT_FILE_BYTES = 100_000
_IGNORED_DIRS = frozenset({"__pycache__", ".pytest_cache", ".venv", ".git", "node_modules"})
_IGNORED_FILES = frozenset({".DS_Store"})
_IGNORED_SUFFIXES = frozenset({".pyc"})


@dataclass
class PageDoc:
    slug: str
    title: str
    kind: str
    position: int
    published: bool
    body: str
    hints: list[str]


@dataclass
class BuildModuleDoc:
    slug: str
    title: str
    summary: str
    position: int
    published: bool
    checkpoint: list[dict[str, str]]
    pages: list[PageDoc] = field(default_factory=list)


@dataclass
class ProjectDoc:
    slug: str
    title: str
    description: str
    position: int
    published: bool
    modules: list[BuildModuleDoc] = field(default_factory=list)


# ---------------------------------------------------------------- parsing


def _kind(meta: dict[str, Any], path: Path) -> str:
    kind = meta.get("kind", "explain")
    if kind not in PAGE_KINDS:
        raise ContentError(f"{path}: kind must be one of: {', '.join(PAGE_KINDS)}.")
    return kind


def _hints(meta: dict[str, Any], path: Path) -> list[str]:
    raw = meta.get("hints")
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(
        isinstance(h, str) and h.strip() for h in raw
    ):
        raise ContentError(f"{path}: 'hints' must be a list of non-empty text items.")
    if len(raw) > MAX_HINTS:
        raise ContentError(f"{path}: 'hints' may have at most {MAX_HINTS} items.")
    hints = [h.strip() for h in raw]
    if any(len(h) > MAX_HINT_LENGTH for h in hints):
        raise ContentError(
            f"{path}: each hint may be at most {MAX_HINT_LENGTH} characters."
        )
    return hints


def _load_page(path: Path) -> PageDoc:
    meta, body = read_document(path)
    if not body:
        raise ContentError(f"{path}: the page text is empty.")
    return PageDoc(
        slug=_slug(meta, path),
        title=_text(meta, "title", path, 200),
        kind=_kind(meta, path),
        position=_position(meta, path),
        published=_published(meta, path),
        body=body,
        hints=_hints(meta, path),
    )


def _load_checkpoint(module_dir: Path) -> list[dict[str, str]]:
    root = module_dir / CHECKPOINT_DIR
    if not root.is_dir():
        return []
    files: list[dict[str, str]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if (
            any(part in _IGNORED_DIRS for part in relative.parts[:-1])
            or path.name in _IGNORED_FILES
            or path.suffix in _IGNORED_SUFFIXES
        ):
            continue
        raw = path.read_bytes()
        if len(raw) > MAX_CHECKPOINT_FILE_BYTES:
            raise ContentError(
                f"{path}: checkpoint files may be at most "
                f"{MAX_CHECKPOINT_FILE_BYTES} bytes."
            )
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ContentError(f"{path}: checkpoint files must be UTF-8 text.") from None
        files.append(
            {"path": relative.as_posix(), "content": text.replace("\r\n", "\n")}
        )
    if len(files) > MAX_CHECKPOINT_FILES:
        raise ContentError(
            f"{root}: at most {MAX_CHECKPOINT_FILES} checkpoint files are allowed."
        )
    files.sort(key=lambda f: f["path"])
    return files


def _load_module(module_dir: Path) -> BuildModuleDoc:
    module_file = _require_file(module_dir / "module.md")
    meta, summary = read_document(module_file)
    module = BuildModuleDoc(
        slug=_slug(meta, module_file),
        title=_text(meta, "title", module_file, 200),
        summary=summary,
        position=_position(meta, module_file),
        published=_published(meta, module_file),
        checkpoint=_load_checkpoint(module_dir),
    )
    for page_file in sorted(module_dir.glob("*.md")):
        if page_file.name == "module.md" or page_file.name.startswith(("_", ".")):
            continue
        module.pages.append(_load_page(page_file))
    _ensure_unique([p.slug for p in module.pages], "page", module_dir)
    return module


def _load_project(project_dir: Path) -> ProjectDoc:
    project_file = _require_file(project_dir / "project.md")
    meta, description = read_document(project_file)
    project = ProjectDoc(
        slug=_slug(meta, project_file),
        title=_text(meta, "title", project_file, 200),
        description=description,
        position=_position(meta, project_file),
        published=_published(meta, project_file),
    )
    for module_dir in _content_dirs(project_dir):
        project.modules.append(_load_module(module_dir))
    _ensure_unique([m.slug for m in project.modules], "module", project_dir)
    return project


def load_build_content(root: Path) -> list[ProjectDoc]:
    """All projects under <root>/build. A missing folder means no projects yet."""
    build_dir = root / "build"
    if not build_dir.is_dir():
        return []
    projects = [_load_project(d) for d in _content_dirs(build_dir)]
    _ensure_unique([p.slug for p in projects], "project", build_dir)
    return projects


# ---------------------------------------------------------------- syncing


async def sync_build(
    session: AsyncSession, projects: list[ProjectDoc]
) -> Counter[str]:
    stats: Counter[str] = Counter()

    project_rows = {row.slug: row for row in await session.scalars(select(Project))}
    module_rows = {
        (row.project_id, row.slug): row
        for row in await session.scalars(select(ProjectModule))
    }
    page_rows = {
        (row.module_id, row.slug): row
        for row in await session.scalars(select(ProjectPage))
    }
    seen_projects: set[int] = set()
    seen_modules: set[int] = set()
    seen_pages: set[int] = set()

    for pd in projects:
        project = _apply(
            session,
            Project,
            project_rows.get(pd.slug),
            {
                "slug": pd.slug,
                "title": pd.title,
                "description": pd.description,
                "position": pd.position,
                "is_published": pd.published,
            },
            stats,
            "projects",
        )
        await session.flush()  # new rows need their ID for the children below
        seen_projects.add(project.id)

        for md in pd.modules:
            module = _apply(
                session,
                ProjectModule,
                module_rows.get((project.id, md.slug)),
                {
                    "project_id": project.id,
                    "slug": md.slug,
                    "title": md.title,
                    "summary": md.summary,
                    "position": md.position,
                    "is_published": md.published,
                    "checkpoint": md.checkpoint,
                },
                stats,
                "project modules",
            )
            await session.flush()
            seen_modules.add(module.id)

            for gd in md.pages:
                page = _apply(
                    session,
                    ProjectPage,
                    page_rows.get((module.id, gd.slug)),
                    {
                        "project_id": project.id,
                        "module_id": module.id,
                        "slug": gd.slug,
                        "title": gd.title,
                        "kind": gd.kind,
                        "body": gd.body,
                        "hints": gd.hints,
                        "position": gd.position,
                        "is_published": gd.published,
                    },
                    stats,
                    "project pages",
                )
                await session.flush()
                seen_pages.add(page.id)

    # Content that disappeared from the files is hidden, never deleted,
    # so student progress is kept.
    for rows, seen, label in (
        (project_rows.values(), seen_projects, "projects"),
        (module_rows.values(), seen_modules, "project modules"),
        (page_rows.values(), seen_pages, "project pages"),
    ):
        for row in rows:
            if row.id not in seen and row.is_published:
                row.is_published = False
                stats[f"{label} unpublished"] += 1

    return stats
