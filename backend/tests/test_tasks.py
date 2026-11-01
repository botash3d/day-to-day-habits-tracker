from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

BASE = "/api/v1/tasks"


async def create(client, headers, title="Task", **fields):
    response = await client.post(BASE, json={"title": title, **fields}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def open_tasks(client, headers):
    return (await client.get(BASE, headers=headers)).json()


async def test_requires_login(client):
    assert (await client.get(BASE)).status_code == 401


async def test_create_applies_defaults(client, login_as):
    headers = await login_as("a@example.com")
    task = await create(client, headers, "  Buy milk  ")
    assert task["title"] == "Buy milk"
    assert task["priority"] == "medium"
    assert task["repeat"] == "none"
    assert task["due_date"] is None
    assert task["category"] is None
    assert task["completed_at"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"title": "   "},
        {"title": "x", "priority": "urgent"},
        {"title": "x", "repeat": "daily"},
        {"title": "x", "repeat": "yearly", "due_date": "2026-11-01"},
    ],
)
async def test_invalid_create_is_rejected(client, login_as, payload):
    headers = await login_as("a@example.com")
    assert (await client.post(BASE, json=payload, headers=headers)).status_code == 422


async def test_open_tasks_are_ordered(client, login_as):
    headers = await login_as("a@example.com")
    await create(client, headers, "no date")
    await create(client, headers, "later low", due_date="2026-11-02", priority="low")
    await create(client, headers, "soon medium", due_date="2026-11-01")
    await create(client, headers, "soon high", due_date="2026-11-01", priority="high")

    titles = [t["title"] for t in await open_tasks(client, headers)]
    assert titles == ["soon high", "soon medium", "later low", "no date"]


async def test_update_task(client, login_as):
    headers = await login_as("a@example.com")
    task = await create(client, headers, "Old", due_date="2026-11-01", category="Home")
    response = await client.patch(
        f"{BASE}/{task['id']}",
        json={"title": "New", "due_date": None, "category": " "},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New"
    assert body["due_date"] is None
    assert body["category"] is None


async def test_update_rejects_null_title(client, login_as):
    headers = await login_as("a@example.com")
    task = await create(client, headers)
    response = await client.patch(f"{BASE}/{task['id']}", json={"title": None}, headers=headers)
    assert response.status_code == 422


async def test_cannot_make_a_task_repeat_without_a_due_date(client, login_as):
    headers = await login_as("a@example.com")
    task = await create(client, headers)
    response = await client.patch(f"{BASE}/{task['id']}", json={"repeat": "daily"}, headers=headers)
    assert response.status_code == 422


async def test_complete_and_reopen(client, login_as):
    headers = await login_as("a@example.com")
    task = await create(client, headers)

    done = await client.post(f"{BASE}/{task['id']}/complete", headers=headers)
    assert done.status_code == 200
    assert done.json()["completed_at"] is not None
    assert await open_tasks(client, headers) == []

    completed = (await client.get(BASE, params={"status": "completed"}, headers=headers)).json()
    assert [t["id"] for t in completed] == [task["id"]]

    assert (await client.post(f"{BASE}/{task['id']}/complete", headers=headers)).status_code == 409

    reopened = await client.post(f"{BASE}/{task['id']}/reopen", headers=headers)
    assert reopened.status_code == 200
    assert reopened.json()["completed_at"] is None
    assert (await client.post(f"{BASE}/{task['id']}/reopen", headers=headers)).status_code == 409


async def test_completing_a_repeating_task_creates_the_next_one(client, login_as):
    headers = await login_as("a@example.com")
    zone = ZoneInfo("Asia/Kolkata")
    today = datetime.now(zone).date()
    task = await create(
        client, headers, "Water plants",
        due_date=(today - timedelta(days=3)).isoformat(),
        repeat="daily", priority="high", category="Home",
    )

    done = await client.post(
        f"{BASE}/{task['id']}/complete", params={"tz": "Asia/Kolkata"}, headers=headers
    )
    assert done.status_code == 200
    assert done.json()["repeat"] == "none"

    tasks = await open_tasks(client, headers)
    assert len(tasks) == 1
    following = tasks[0]
    assert following["id"] != task["id"]
    assert following["title"] == "Water plants"
    assert following["priority"] == "high"
    assert following["category"] == "Home"
    assert following["repeat"] == "daily"
    assert following["due_date"] == (today + timedelta(days=1)).isoformat()


async def test_unknown_timezone_is_rejected(client, login_as):
    headers = await login_as("a@example.com")
    task = await create(client, headers)
    response = await client.post(
        f"{BASE}/{task['id']}/complete", params={"tz": "Not/AZone"}, headers=headers
    )
    assert response.status_code == 422


async def test_completed_tasks_cannot_be_edited(client, login_as):
    headers = await login_as("a@example.com")
    task = await create(client, headers)
    await client.post(f"{BASE}/{task['id']}/complete", headers=headers)
    response = await client.patch(
        f"{BASE}/{task['id']}", json={"title": "Changed"}, headers=headers
    )
    assert response.status_code == 409


async def test_delete_task(client, login_as):
    headers = await login_as("a@example.com")
    task = await create(client, headers)
    assert (await client.delete(f"{BASE}/{task['id']}", headers=headers)).status_code == 204
    assert (await client.delete(f"{BASE}/{task['id']}", headers=headers)).status_code == 404


async def test_tasks_are_private_to_their_owner(client, login_as):
    owner = await login_as("owner@example.com")
    other = await login_as("other@example.com")
    task = await create(client, owner, "Secret")

    assert await open_tasks(client, other) == []
    for method, url, kwargs in [
        ("patch", f"{BASE}/{task['id']}", {"json": {"title": "Hacked"}}),
        ("post", f"{BASE}/{task['id']}/complete", {}),
        ("post", f"{BASE}/{task['id']}/reopen", {}),
        ("delete", f"{BASE}/{task['id']}", {}),
    ]:
        response = await getattr(client, method)(url, headers=other, **kwargs)
        assert response.status_code == 404, (method, url)