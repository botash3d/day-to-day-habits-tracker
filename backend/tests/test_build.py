import pytest

from app.models.build import Project, ProjectModule, ProjectPage

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/build"
PAGES = f"{BASE}/projects/shortener/modules"

SETUP_CHECKPOINT = [
    {"path": "main.py", "content": "print('done')\n"},
    {"path": "test_app.py", "content": "def test_x():\n    pass\n"},
]


async def seed_project(session_factory) -> None:
    """One visible project with 4 visible pages in 2 modules, plus assorted drafts."""
    async with session_factory() as session:
        shortener = Project(
            slug="shortener", title="URL Shortener", description="Build it.",
            position=1, is_published=True,
        )
        secret = Project(slug="secret", title="Secret", position=2, is_published=False)
        session.add_all([shortener, secret])
        await session.flush()

        def make_module(project, slug, title, position, published=True, checkpoint=None):
            return ProjectModule(
                project_id=project.id, slug=slug, title=title, summary=f"About {title}.",
                position=position, is_published=published, checkpoint=checkpoint or [],
            )

        setup = make_module(shortener, "setup", "Setup", 1, checkpoint=SETUP_CHECKPOINT)
        basic = make_module(shortener, "basic", "Basic app", 2)
        hidden = make_module(shortener, "hidden-module", "Hidden", 3, published=False)
        secret_module = make_module(secret, "secret-module", "Secret module", 1)
        # Inserted out of order on purpose: ordering must come from position.
        session.add_all([basic, hidden, secret_module, setup])
        await session.flush()

        def make_page(project, module, slug, title, position, **extra):
            return ProjectPage(
                project_id=project.id, module_id=module.id, slug=slug, title=title,
                body=f"# {title}\n\nBody of {title}.", position=position,
                kind=extra.get("kind", "explain"), hints=extra.get("hints", []),
                is_published=extra.get("published", True),
            )

        session.add_all(
            [
                make_page(
                    shortener, setup, "stuck", "Stuck?", 3,
                    kind="stuck", hints=["First hint.", "Second hint."],
                ),
                make_page(shortener, setup, "goal", "Goal", 1),
                make_page(shortener, setup, "check", "Check", 2, kind="check"),
                make_page(shortener, setup, "draft-page", "Draft", 4, published=False),
                # Same slug as the first page of "setup": slugs are per module.
                make_page(shortener, basic, "goal", "Basic goal", 1),
                make_page(shortener, hidden, "in-hidden", "In hidden", 1),
                make_page(secret, secret_module, "secret-page", "Secret page", 1),
            ]
        )
        await session.commit()


def page_url(module: str, page: str) -> str:
    return f"{PAGES}/{module}/pages/{page}"


async def complete(client, headers, module: str, page: str):
    return await client.put(f"{page_url(module, page)}/progress", headers=headers)


async def test_build_endpoints_require_login(client, session_factory):
    await seed_project(session_factory)
    assert (await client.get(f"{BASE}/projects")).status_code == 401
    assert (await client.get(f"{BASE}/projects/shortener")).status_code == 401
    assert (await client.get(page_url("setup", "goal"))).status_code == 401
    assert (await client.put(f"{page_url('setup', 'goal')}/progress")).status_code == 401
    assert (await client.delete(f"{page_url('setup', 'goal')}/progress")).status_code == 401


async def test_list_projects_hides_drafts_and_counts_visible_pages(
    client, session_factory, login_as
):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    response = await client.get(f"{BASE}/projects", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert [p["slug"] for p in data] == ["shortener"]
    assert data[0]["title"] == "URL Shortener"
    assert data[0]["module_count"] == 2  # the hidden module is not counted
    assert data[0]["page_count"] == 4  # draft and hidden-module pages are not counted
    assert data[0]["completed_count"] == 0


async def test_project_detail_is_ordered_and_hides_drafts(
    client, session_factory, login_as
):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    response = await client.get(f"{BASE}/projects/shortener", headers=headers)

    assert response.status_code == 200
    data = response.json()
    setup, basic = data["modules"]
    assert [m["slug"] for m in data["modules"]] == ["setup", "basic"]
    assert setup["summary"] == "About Setup."
    assert [p["slug"] for p in setup["pages"]] == ["goal", "check", "stuck"]
    assert [p["kind"] for p in setup["pages"]] == ["explain", "check", "stuck"]
    assert [p["slug"] for p in basic["pages"]] == ["goal"]
    assert setup["page_count"] == 3
    assert setup["completed_count"] == 0
    assert data["page_count"] == 4
    assert data["next_page"] == {"module_slug": "setup", "page_slug": "goal", "title": "Goal"}


@pytest.mark.parametrize("slug", ["secret", "nope"])
async def test_unknown_or_draft_project_is_404(client, session_factory, login_as, slug):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    response = await client.get(f"{BASE}/projects/{slug}", headers=headers)

    assert response.status_code == 404


async def test_page_detail_includes_body_position_and_neighbours(
    client, session_factory, login_as
):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    response = await client.get(page_url("setup", "goal"), headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Goal"
    assert data["kind"] == "explain"
    assert data["body"] == "# Goal\n\nBody of Goal."
    assert data["hints"] == []
    assert data["project_slug"] == "shortener"
    assert data["project_title"] == "URL Shortener"
    assert data["module_slug"] == "setup"
    assert data["module_title"] == "Setup"
    assert data["page_number"] == 1
    assert data["module_page_count"] == 3
    assert data["completed"] is False
    assert data["completed_at"] is None
    assert data["previous"] is None
    assert data["next"] == {"module_slug": "setup", "page_slug": "check", "title": "Check"}


@pytest.mark.parametrize("page", ["goal", "check"])
async def test_checkpoint_is_only_sent_on_stuck_pages(
    client, session_factory, login_as, page
):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    data = (await client.get(page_url("setup", page), headers=headers)).json()

    assert data["checkpoint"] == []


async def test_stuck_page_includes_hints_and_the_modules_checkpoint(
    client, session_factory, login_as
):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    data = (await client.get(page_url("setup", "stuck"), headers=headers)).json()

    assert data["kind"] == "stuck"
    assert data["page_number"] == 3
    assert data["hints"] == ["First hint.", "Second hint."]
    assert data["checkpoint"] == SETUP_CHECKPOINT


async def test_neighbours_cross_module_boundaries(client, session_factory, login_as):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    last_of_setup = (await client.get(page_url("setup", "stuck"), headers=headers)).json()
    first_of_basic = (await client.get(page_url("basic", "goal"), headers=headers)).json()

    assert last_of_setup["next"] == {
        "module_slug": "basic", "page_slug": "goal", "title": "Basic goal",
    }
    assert first_of_basic["previous"] == {
        "module_slug": "setup", "page_slug": "stuck", "title": "Stuck?",
    }
    assert first_of_basic["next"] is None
    assert first_of_basic["page_number"] == 1
    assert first_of_basic["module_page_count"] == 1


async def test_same_page_slug_in_two_modules_is_resolved_by_module(
    client, session_factory, login_as
):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    first = (await client.get(page_url("setup", "goal"), headers=headers)).json()
    second = (await client.get(page_url("basic", "goal"), headers=headers)).json()

    assert first["title"] == "Goal"
    assert second["title"] == "Basic goal"

    await complete(client, headers, "setup", "goal")

    after_first = (await client.get(page_url("setup", "goal"), headers=headers)).json()
    after_second = (await client.get(page_url("basic", "goal"), headers=headers)).json()
    assert after_first["completed"] is True
    assert after_second["completed"] is False


@pytest.mark.parametrize(
    "path",
    [
        "/projects/shortener/modules/setup/pages/draft-page",  # draft page
        "/projects/shortener/modules/hidden-module/pages/in-hidden",  # unpublished module
        "/projects/shortener/modules/setup/pages/nope",  # does not exist
        "/projects/shortener/modules/basic/pages/stuck",  # page of another module
        "/projects/shortener/modules/nope/pages/goal",  # unknown module
        "/projects/secret/modules/secret-module/pages/secret-page",  # draft project
        "/projects/nope/modules/setup/pages/goal",  # unknown project
    ],
)
async def test_hidden_pages_are_404_for_reading_and_progress(
    client, session_factory, login_as, path
):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    read = await client.get(f"{BASE}{path}", headers=headers)
    put = await client.put(f"{BASE}{path}/progress", headers=headers)
    delete = await client.delete(f"{BASE}{path}/progress", headers=headers)

    assert read.status_code == 404
    assert put.status_code == 404
    assert delete.status_code == 404


async def test_mark_complete_is_idempotent_and_updates_progress(
    client, session_factory, login_as
):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    first = await complete(client, headers, "setup", "goal")
    second = await complete(client, headers, "setup", "goal")

    assert first.status_code == 200
    assert first.json()["completed"] is True
    assert first.json()["completed_at"] is not None
    assert second.status_code == 200
    assert second.json()["completed_at"] == first.json()["completed_at"]

    page = (await client.get(page_url("setup", "goal"), headers=headers)).json()
    assert page["completed"] is True
    assert page["completed_at"] is not None

    project = (await client.get(f"{BASE}/projects/shortener", headers=headers)).json()
    assert project["completed_count"] == 1
    assert project["modules"][0]["completed_count"] == 1
    assert project["modules"][0]["pages"][0]["completed"] is True
    assert project["next_page"] == {
        "module_slug": "setup", "page_slug": "check", "title": "Check",
    }

    listing = (await client.get(f"{BASE}/projects", headers=headers)).json()
    assert listing[0]["completed_count"] == 1


async def test_completing_everything_clears_next_page(client, session_factory, login_as):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    pages = [("setup", "goal"), ("setup", "check"), ("setup", "stuck"), ("basic", "goal")]
    for module, page in pages:
        await complete(client, headers, module, page)

    project = (await client.get(f"{BASE}/projects/shortener", headers=headers)).json()
    assert project["completed_count"] == 4
    assert project["next_page"] is None


async def test_next_page_skips_to_first_incomplete(client, session_factory, login_as):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)

    await complete(client, headers, "setup", "check")  # skipped "goal"

    project = (await client.get(f"{BASE}/projects/shortener", headers=headers)).json()
    assert project["next_page"] == {
        "module_slug": "setup", "page_slug": "goal", "title": "Goal",
    }


async def test_undo_progress_is_idempotent(client, session_factory, login_as):
    headers = await login_as("a@example.com")
    await seed_project(session_factory)
    await complete(client, headers, "setup", "goal")

    first = await client.delete(f"{page_url('setup', 'goal')}/progress", headers=headers)
    second = await client.delete(f"{page_url('setup', 'goal')}/progress", headers=headers)

    assert first.status_code == 204
    assert second.status_code == 204
    page = (await client.get(page_url("setup", "goal"), headers=headers)).json()
    assert page["completed"] is False
    assert page["completed_at"] is None


async def test_progress_is_per_user(client, session_factory, login_as):
    alice = await login_as("alice@example.com")
    bob = await login_as("bob@example.com")
    await seed_project(session_factory)

    await complete(client, alice, "setup", "goal")

    alice_view = (await client.get(page_url("setup", "goal"), headers=alice)).json()
    bob_view = (await client.get(page_url("setup", "goal"), headers=bob)).json()
    bob_project = (await client.get(f"{BASE}/projects/shortener", headers=bob)).json()
    assert alice_view["completed"] is True
    assert bob_view["completed"] is False
    assert bob_project["completed_count"] == 0