import pytest

from app.models.learn import Exercise, Lesson, Module, Subject

pytestmark = pytest.mark.asyncio

BASE = "/api/v1/learn"
LESSONS = f"{BASE}/subjects/python/lessons"


async def seed_course(session_factory) -> None:
    """One visible subject with 3 visible lessons, plus assorted drafts."""
    async with session_factory() as session:
        python = Subject(
            slug="python", title="Python", description="Learn Python.",
            position=1, is_published=True,
        )
        secret = Subject(slug="secret", title="Secret", position=2, is_published=False)
        session.add_all([python, secret])
        await session.flush()

        basics = Module(
            subject_id=python.id, slug="basics", title="Basics",
            position=1, is_published=True,
        )
        advanced = Module(
            subject_id=python.id, slug="advanced", title="Advanced",
            position=2, is_published=True,
        )
        hidden = Module(
            subject_id=python.id, slug="hidden-module", title="Hidden",
            position=3, is_published=False,
        )
        secret_module = Module(
            subject_id=secret.id, slug="secret-module", title="Secret",
            position=1, is_published=True,
        )
        # Inserted out of order on purpose: ordering must come from position.
        session.add_all([advanced, hidden, secret_module, basics])
        await session.flush()

        def make_lesson(subject, module, slug, title, position, published=True):
            return Lesson(
                subject_id=subject.id, module_id=module.id, slug=slug, title=title,
                body=f"# {title}\n\nBody of {title}.",
                position=position, is_published=published,
            )

        hello = make_lesson(python, basics, "hello", "Hello", 1)
        session.add_all(
            [
                make_lesson(python, basics, "variables", "Variables", 2),
                hello,
                make_lesson(python, basics, "draft-lesson", "Draft", 3, published=False),
                make_lesson(python, advanced, "functions", "Functions", 1),
                make_lesson(python, hidden, "in-hidden-module", "In hidden", 1),
                make_lesson(secret, secret_module, "secret-lesson", "Secret", 1),
            ]
        )
        await session.flush()

        session.add(
            Exercise(
                lesson_id=hello.id,
                kind="local",
                steps=[
                    {
                        "instruction": "Run it.",
                        "command": "python hello.py",
                        "expected_output": "Hello",
                        "check": "You see Hello.",
                    },
                    {"instruction": "Only an instruction."},
                ],
            )
        )
        await session.commit()


async def complete(client, headers, lesson_slug: str):
    return await client.put(f"{LESSONS}/{lesson_slug}/progress", headers=headers)


async def test_learn_endpoints_require_login(client, session_factory):
    await seed_course(session_factory)
    assert (await client.get(f"{BASE}/subjects")).status_code == 401
    assert (await client.get(f"{BASE}/subjects/python")).status_code == 401
    assert (await client.get(f"{LESSONS}/hello")).status_code == 401
    assert (await client.put(f"{LESSONS}/hello/progress")).status_code == 401
    assert (await client.delete(f"{LESSONS}/hello/progress")).status_code == 401


async def test_list_subjects_hides_drafts_and_counts_visible_lessons(
    client, session_factory, login_as
):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)

    response = await client.get(f"{BASE}/subjects", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert [s["slug"] for s in data] == ["python"]
    assert data[0]["title"] == "Python"
    assert data[0]["lesson_count"] == 3  # drafts and hidden modules not counted
    assert data[0]["completed_count"] == 0


async def test_subject_detail_is_ordered_and_hides_drafts(
    client, session_factory, login_as
):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)

    response = await client.get(f"{BASE}/subjects/python", headers=headers)

    assert response.status_code == 200
    data = response.json()
    basics, advanced = data["modules"][0], data["modules"][1]
    assert [m["slug"] for m in data["modules"]] == ["basics", "advanced"]
    assert [x["slug"] for x in basics["lessons"]] == ["hello", "variables"]
    assert [x["slug"] for x in advanced["lessons"]] == ["functions"]
    assert not any(
        x["completed"] for module in data["modules"] for x in module["lessons"]
    )
    assert data["lesson_count"] == 3
    assert data["next_lesson_slug"] == "hello"

@pytest.mark.parametrize("slug", ["secret", "nope"])
async def test_unknown_or_draft_subject_is_404(
    client, session_factory, login_as, slug
):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)

    response = await client.get(f"{BASE}/subjects/{slug}", headers=headers)

    assert response.status_code == 404


async def test_lesson_detail_includes_body_exercise_and_neighbours(
    client, session_factory, login_as
):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)

    response = await client.get(f"{LESSONS}/hello", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Hello"
    assert data["body"] == "# Hello\n\nBody of Hello."
    assert data["subject_slug"] == "python"
    assert data["module_title"] == "Basics"
    assert data["completed"] is False
    assert data["previous_slug"] is None
    assert data["next_slug"] == "variables"
    assert data["exercise"]["kind"] == "local"
    steps = data["exercise"]["steps"]
    assert len(steps) == 2
    assert steps[0]["command"] == "python hello.py"
    # Missing keys come back as empty strings, not errors.
    assert steps[1] == {
        "instruction": "Only an instruction.",
        "command": "",
        "expected_output": "",
        "check": "",
    }


async def test_neighbours_cross_module_boundaries(client, session_factory, login_as):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)

    middle = (await client.get(f"{LESSONS}/variables", headers=headers)).json()
    last = (await client.get(f"{LESSONS}/functions", headers=headers)).json()

    assert middle["previous_slug"] == "hello"
    assert middle["next_slug"] == "functions"  # first lesson of the next module
    assert last["previous_slug"] == "variables"
    assert last["next_slug"] is None


async def test_lesson_without_exercise_returns_null(client, session_factory, login_as):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)

    data = (await client.get(f"{LESSONS}/variables", headers=headers)).json()

    assert data["exercise"] is None


@pytest.mark.parametrize(
    "path",
    [
        "/subjects/python/lessons/draft-lesson",  # draft lesson
        "/subjects/python/lessons/in-hidden-module",  # lesson in an unpublished module
        "/subjects/python/lessons/nope",  # does not exist
        "/subjects/python/lessons/secret-lesson",  # belongs to another subject
        "/subjects/secret/lessons/secret-lesson",  # draft subject
    ],
)
async def test_hidden_lessons_are_404(client, session_factory, login_as, path):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)

    response = await client.get(f"{BASE}{path}", headers=headers)

    assert response.status_code == 404


async def test_mark_complete_is_idempotent_and_updates_progress(
    client, session_factory, login_as
):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)

    first = await complete(client, headers, "hello")
    second = await complete(client, headers, "hello")

    assert first.status_code == 200
    assert first.json()["completed"] is True
    assert first.json()["completed_at"] is not None
    assert second.status_code == 200
    assert second.json()["completed_at"] == first.json()["completed_at"]

    lesson = (await client.get(f"{LESSONS}/hello", headers=headers)).json()
    assert lesson["completed"] is True
    assert lesson["completed_at"] is not None

    subject = (await client.get(f"{BASE}/subjects/python", headers=headers)).json()
    assert subject["completed_count"] == 1
    assert subject["modules"][0]["lessons"][0]["completed"] is True
    assert subject["next_lesson_slug"] == "variables"

    listing = (await client.get(f"{BASE}/subjects", headers=headers)).json()
    assert listing[0]["completed_count"] == 1


async def test_completing_everything_clears_next_lesson(
    client, session_factory, login_as
):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)

    for slug in ("hello", "variables", "functions"):
        await complete(client, headers, slug)

    subject = (await client.get(f"{BASE}/subjects/python", headers=headers)).json()
    assert subject["completed_count"] == 3
    assert subject["next_lesson_slug"] is None


async def test_next_lesson_skips_to_first_incomplete(client, session_factory, login_as):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)

    await complete(client, headers, "variables")  # skipped "hello"

    subject = (await client.get(f"{BASE}/subjects/python", headers=headers)).json()
    assert subject["next_lesson_slug"] == "hello"


async def test_undo_progress_is_idempotent(client, session_factory, login_as):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)
    await complete(client, headers, "hello")

    first = await client.delete(f"{LESSONS}/hello/progress", headers=headers)
    second = await client.delete(f"{LESSONS}/hello/progress", headers=headers)

    assert first.status_code == 204
    assert second.status_code == 204
    lesson = (await client.get(f"{LESSONS}/hello", headers=headers)).json()
    assert lesson["completed"] is False
    assert lesson["completed_at"] is None


async def test_progress_is_per_user(client, session_factory, login_as):
    alice = await login_as("alice@example.com")
    bob = await login_as("bob@example.com")
    await seed_course(session_factory)

    await complete(client, alice, "hello")

    alice_view = (await client.get(f"{LESSONS}/hello", headers=alice)).json()
    bob_view = (await client.get(f"{LESSONS}/hello", headers=bob)).json()
    bob_subject = (await client.get(f"{BASE}/subjects/python", headers=bob)).json()
    assert alice_view["completed"] is True
    assert bob_view["completed"] is False
    assert bob_subject["completed_count"] == 0


@pytest.mark.parametrize("slug", ["draft-lesson", "in-hidden-module", "nope"])
async def test_cannot_change_progress_on_hidden_lessons(
    client, session_factory, login_as, slug
):
    headers = await login_as("a@example.com")
    await seed_course(session_factory)

    put = await complete(client, headers, slug)
    delete = await client.delete(f"{LESSONS}/{slug}/progress", headers=headers)

    assert put.status_code == 404
    assert delete.status_code == 404