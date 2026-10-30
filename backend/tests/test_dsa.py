import pytest_asyncio

from app.models.problem import Problem

URL = "/api/v1/dsa/problems"


async def auth_headers(client):
    creds = {"email": "dsa@example.com", "password": "a-strong-passphrase"}
    await client.post("/api/v1/auth/signup", json={**creds, "full_name": "Dsa User"})
    token = (await client.post("/api/v1/auth/login", json=creds)).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def seeded(session_factory):
    async with session_factory() as session:
        session.add_all(
            [
                Problem(slug="two-sum", title="Two Sum", difficulty="Easy",
                        topic="Arrays", url="https://leetcode.com/problems/two-sum/"),
                Problem(slug="3sum", title="3Sum", difficulty="Medium",
                        topic="Two Pointers", url="https://leetcode.com/problems/3sum/"),
            ]
        )
        await session.commit()


async def test_problems_require_login(client):
    assert (await client.get(URL)).status_code == 401


async def test_list_problems(client, seeded):
    response = await client.get(URL, headers=await auth_headers(client))
    assert response.status_code == 200
    assert [p["title"] for p in response.json()] == ["Two Sum", "3Sum"]
    assert response.json()[0]["difficulty"] == "Easy"