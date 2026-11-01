import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.build import Project, ProjectModule, ProjectPage, ProjectPageProgress
from app.schemas.build import (
    CheckpointFile,
    ModuleOutline,
    PageDetail,
    PageProgressPublic,
    PageRef,
    PageSummary,
    ProjectDetail,
    ProjectSummary,
)


class ProjectNotFoundError(Exception):
    pass


class PageNotFoundError(Exception):
    pass


def _as_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes, PostgreSQL returns aware ones.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


@dataclass
class _Outline:
    project: Project
    # Visible pages in project order, each with its module.
    entries: list[tuple[ProjectModule, ProjectPage]]
    # page_id -> when this user completed it.
    completed_at: dict[int, datetime]


def _ref(module: ProjectModule, page: ProjectPage) -> PageRef:
    return PageRef(module_slug=module.slug, page_slug=page.slug, title=page.title)


async def _load_outline(
    session: AsyncSession, user_id: uuid.UUID, project_slug: str
) -> _Outline:
    """Everything a student may see in one project, in project order.

    A page is visible only if its project, its module and the page itself are
    all published. Drafts are indistinguishable from missing content.
    """
    project = await session.scalar(
        select(Project).where(Project.slug == project_slug, Project.is_published.is_(True))
    )
    if project is None:
        raise ProjectNotFoundError

    rows = await session.execute(
        select(ProjectModule, ProjectPage)
        .join(ProjectPage, ProjectPage.module_id == ProjectModule.id)
        .where(
            ProjectModule.project_id == project.id,
            ProjectModule.is_published.is_(True),
            ProjectPage.is_published.is_(True),
        )
        .order_by(
            ProjectModule.position,
            ProjectModule.id,
            ProjectPage.position,
            ProjectPage.id,
        )
    )
    entries = [(module, page) for module, page in rows.all()]

    completed_at: dict[int, datetime] = {}
    page_ids = [page.id for _, page in entries]
    if page_ids:
        progress = await session.execute(
            select(ProjectPageProgress.page_id, ProjectPageProgress.completed_at).where(
                ProjectPageProgress.user_id == user_id,
                ProjectPageProgress.page_id.in_(page_ids),
            )
        )
        completed_at = {
            page_id: _as_utc(when) for page_id, when in progress.tuples().all()
        }

    return _Outline(project=project, entries=entries, completed_at=completed_at)


def _find_index(outline: _Outline, module_slug: str, page_slug: str) -> int:
    # Page slugs are only unique within a module, so both slugs are needed.
    for index, (module, page) in enumerate(outline.entries):
        if module.slug == module_slug and page.slug == page_slug:
            return index
    raise PageNotFoundError


async def list_projects(
    session: AsyncSession, user_id: uuid.UUID
) -> list[ProjectSummary]:
    projects = await session.scalars(
        select(Project).where(Project.is_published.is_(True)).order_by(Project.position, Project.id)
    )
    visible = (ProjectModule.is_published.is_(True), ProjectPage.is_published.is_(True))

    totals_result = await session.execute(
        select(
            ProjectModule.project_id,
            func.count(ProjectPage.id),
            func.count(ProjectModule.id.distinct()),
        )
        .join(ProjectPage, ProjectPage.module_id == ProjectModule.id)
        .where(*visible)
        .group_by(ProjectModule.project_id)
    )
    totals = {
        project_id: (pages, modules)
        for project_id, pages, modules in totals_result.all()
    }

    done_result = await session.execute(
        select(ProjectModule.project_id, func.count(ProjectPage.id))
        .join(ProjectPage, ProjectPage.module_id == ProjectModule.id)
        .join(ProjectPageProgress, ProjectPageProgress.page_id == ProjectPage.id)
        .where(ProjectPageProgress.user_id == user_id, *visible)
        .group_by(ProjectModule.project_id)
    )
    done = dict(done_result.tuples().all())

    return [
        ProjectSummary(
            slug=project.slug,
            title=project.title,
            description=project.description,
            module_count=totals.get(project.id, (0, 0))[1],
            page_count=totals.get(project.id, (0, 0))[0],
            completed_count=done.get(project.id, 0),
        )
        for project in projects
    ]


async def get_project(
    session: AsyncSession, user_id: uuid.UUID, project_slug: str
) -> ProjectDetail:
    outline = await _load_outline(session, user_id, project_slug)

    modules: list[ModuleOutline] = []
    current_module_id: int | None = None
    for module, page in outline.entries:
        if module.id != current_module_id:
            modules.append(
                ModuleOutline(
                    slug=module.slug,
                    title=module.title,
                    summary=module.summary,
                    page_count=0,
                    completed_count=0,
                    pages=[],
                )
            )
            current_module_id = module.id
        done = page.id in outline.completed_at
        current = modules[-1]
        current.pages.append(
            PageSummary(slug=page.slug, title=page.title, kind=page.kind, completed=done)
        )
        current.page_count += 1
        if done:
            current.completed_count += 1

    next_page = next(
        (
            _ref(module, page)
            for module, page in outline.entries
            if page.id not in outline.completed_at
        ),
        None,
    )
    return ProjectDetail(
        slug=outline.project.slug,
        title=outline.project.title,
        description=outline.project.description,
        module_count=len(modules),
        page_count=len(outline.entries),
        completed_count=len(outline.completed_at),
        modules=modules,
        next_page=next_page,
    )


async def get_page(
    session: AsyncSession,
    user_id: uuid.UUID,
    project_slug: str,
    module_slug: str,
    page_slug: str,
) -> PageDetail:
    outline = await _load_outline(session, user_id, project_slug)
    index = _find_index(outline, module_slug, page_slug)
    module, page = outline.entries[index]

    module_page_ids = [p.id for m, p in outline.entries if m.id == module.id]
    checkpoint: list[CheckpointFile] = []
    if page.kind == "stuck":
        checkpoint = [CheckpointFile.model_validate(f) for f in module.checkpoint]

    return PageDetail(
        slug=page.slug,
        title=page.title,
        kind=page.kind,
        body=page.body,
        hints=list(page.hints or []),
        project_slug=outline.project.slug,
        project_title=outline.project.title,
        module_slug=module.slug,
        module_title=module.title,
        page_number=module_page_ids.index(page.id) + 1,
        module_page_count=len(module_page_ids),
        completed=page.id in outline.completed_at,
        completed_at=outline.completed_at.get(page.id),
        previous=_ref(*outline.entries[index - 1]) if index > 0 else None,
        next=(
            _ref(*outline.entries[index + 1])
            if index + 1 < len(outline.entries)
            else None
        ),
        checkpoint=checkpoint,
    )


async def mark_complete(
    session: AsyncSession,
    user_id: uuid.UUID,
    project_slug: str,
    module_slug: str,
    page_slug: str,
) -> PageProgressPublic:
    """Idempotent: completing an already completed page changes nothing."""
    outline = await _load_outline(session, user_id, project_slug)
    _, page = outline.entries[_find_index(outline, module_slug, page_slug)]

    row = await session.get(ProjectPageProgress, (user_id, page.id))
    if row is None:
        row = ProjectPageProgress(
            user_id=user_id, page_id=page.id, completed_at=datetime.now(UTC)
        )
        session.add(row)
        try:
            await session.commit()
        except IntegrityError:
            # A parallel request completed it first. That is fine.
            await session.rollback()
            row = await session.get(ProjectPageProgress, (user_id, page.id))

    return PageProgressPublic(
        slug=page.slug,
        completed=row is not None,
        completed_at=_as_utc(row.completed_at) if row is not None else None,
    )


async def mark_incomplete(
    session: AsyncSession,
    user_id: uuid.UUID,
    project_slug: str,
    module_slug: str,
    page_slug: str,
) -> None:
    """Idempotent: undoing a page that is not completed changes nothing."""
    outline = await _load_outline(session, user_id, project_slug)
    _, page = outline.entries[_find_index(outline, module_slug, page_slug)]

    row = await session.get(ProjectPageProgress, (user_id, page.id))
    if row is not None:
        await session.delete(row)
        await session.commit()