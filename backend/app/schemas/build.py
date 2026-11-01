from datetime import datetime

from pydantic import BaseModel


class PageRef(BaseModel):
    """Points at a page anywhere in a project, for Previous / Next / Continue."""

    module_slug: str
    page_slug: str
    title: str


class ProjectSummary(BaseModel):
    slug: str
    title: str
    description: str
    module_count: int
    page_count: int
    completed_count: int


class PageSummary(BaseModel):
    slug: str
    title: str
    kind: str
    completed: bool


class ModuleOutline(BaseModel):
    slug: str
    title: str
    summary: str
    page_count: int
    completed_count: int
    pages: list[PageSummary]


class ProjectDetail(ProjectSummary):
    modules: list[ModuleOutline]
    # First page the user has not completed, in project order ("continue").
    # None when every page is done or the project has no pages yet.
    next_page: PageRef | None


class CheckpointFile(BaseModel):
    path: str
    content: str


class PageDetail(BaseModel):
    slug: str
    title: str
    kind: str
    body: str
    hints: list[str]
    project_slug: str
    project_title: str
    module_slug: str
    module_title: str
    # Position inside the module, e.g. "page 3 of 7".
    page_number: int
    module_page_count: int
    completed: bool
    completed_at: datetime | None
    previous: PageRef | None
    next: PageRef | None
    # The module's finished code. Only sent on "stuck" pages, otherwise empty.
    checkpoint: list[CheckpointFile]


class PageProgressPublic(BaseModel):
    slug: str
    completed: bool
    completed_at: datetime | None