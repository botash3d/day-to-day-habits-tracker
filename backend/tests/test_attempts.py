import pytest_asyncio

from app.models.problem import Problem

BASE = "/api/v1/dsa"


async def login(client, email):
    creds = {"email": email, "password": "a-strong-passphrase"}
    await client.post("/api/v1/auth/signup", json={**creds, "full_name": "Test User"})
    token = (await client.post("/api/v1/auth/login", json=creds)).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def problem_id(session_factory):
    async with session_factory() as session:
        problem = Problem(
            slug="two-sum", title="Two Sum", difficulty="Easy",
            topic="Arrays", url="https://leetcode.com/problems/two-sum/",
        )
        session.add(problem)
        await session.commit()
        return problem.id


async def test_start_resumes_existing_attempt(client, problem_id):
    headers = await login(client, "a@example.com")
    first = await client.post(f"{BASE}/problems/{problem_id}/attempts", headers=headers)
    assert first.status_code == 201
    second = await client.post(f"{BASE}/problems/{problem_id}/attempts", headers=headers)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


async def test_problem_detail_includes_active_attempt(client, problem_id):
    headers = await login(client, "a@example.com")
    detail = await client.get(f"{BASE}/problems/{problem_id}", headers=headers)
    assert detail.json()["active_attempt"] is None

    attempt = (await client.post(f"{BASE}/problems/{problem_id}/attempts", headers=headers)).json()
    detail = await client.get(f"{BASE}/problems/{problem_id}", headers=headers)
    assert detail.json()["active_attempt"]["id"] == attempt["id"]


async def test_finish_attempt(client, problem_id):
    headers = await login(client, "a@example.com")
    attempt = (await client.post(f"{BASE}/problems/{problem_id}/attempts", headers=headers)).json()

    done = await client.post(
        f"{BASE}/attempts/{attempt['id']}/finish",
        json={"solution_url": "https://github.com/me/solution"},
        headers=headers,
    )
    assert done.status_code == 200
    body = done.json()
    assert body["finished_at"] is not None
    assert body["duration_seconds"] >= 0
    assert body["solution_url"] == "https://github.com/me/solution"

    again = await client.post(f"{BASE}/attempts/{attempt['id']}/finish", json={}, headers=headers)
    assert again.status_code == 409

    restart = await client.post(f"{BASE}/problems/{problem_id}/attempts", headers=headers)
    assert restart.status_code == 201
    assert restart.json()["id"] != attempt["id"]


async def test_rejects_non_http_solution_url(client, problem_id):
    headers = await login(client, "a@example.com")
    attempt = (await client.post(f"{BASE}/problems/{problem_id}/attempts", headers=headers)).json()
    response = await client.post(
        f"{BASE}/attempts/{attempt['id']}/finish",
        json={"solution_url": "javascript:alert(1)"},
        headers=headers,
    )
    assert response.status_code == 422


async def test_cannot_touch_another_users_attempt(client, problem_id):
    owner = await login(client, "owner@example.com")
    other = await login(client, "other@example.com")
    attempt = (await client.post(f"{BASE}/problems/{problem_id}/attempts", headers=owner)).json()

    finish = await client.post(f"{BASE}/attempts/{attempt['id']}/finish", json={}, headers=other)
    assert finish.status_code == 404
    discard = await client.delete(f"{BASE}/attempts/{attempt['id']}", headers=other)
    assert discard.status_code == 404


async def test_discard_only_unfinished(client, problem_id):
    headers = await login(client, "a@example.com")
    first = (await client.post(f"{BASE}/problems/{problem_id}/attempts", headers=headers)).json()
    response = await client.delete(f"{BASE}/attempts/{first['id']}", headers=headers)
    assert response.status_code == 204
    second = (await client.post(f"{BASE}/problems/{problem_id}/attempts", headers=headers)).json()
    await client.post(f"{BASE}/attempts/{second['id']}/finish", json={}, headers=headers)
    response = await client.delete(f"{BASE}/attempts/{second['id']}", headers=headers)
    assert response.status_code == 409

async def test_unknown_problem_is_404(client):
    headers = await login(client, "a@example.com")
    response = await client.post(f"{BASE}/problems/9999/attempts", headers=headers)
    assert response.status_code == 404