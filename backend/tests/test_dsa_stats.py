import pytest_asyncio

from app.models.problem import Problem

BASE = "/api/v1/dsa"


@pytest_asyncio.fixture
async def problem_ids(session_factory):
    async with session_factory() as session:
        first = Problem(slug="two-sum", title="Two Sum", difficulty="Easy",
                        topic="Arrays", url="https://leetcode.com/problems/two-sum/")
        second = Problem(slug="3sum", title="3Sum", difficulty="Medium",
                         topic="Two Pointers", url="https://leetcode.com/problems/3sum/")
        session.add_all([first, second])
        await session.commit()
        return [first.id, second.id]


async def solve(client, headers, problem_id):
    attempt = (await client.post(f"{BASE}/problems/{problem_id}/attempts", headers=headers)).json()
    done = await client.post(f"{BASE}/attempts/{attempt['id']}/finish", json={}, headers=headers)
    assert done.status_code == 200


async def test_list_includes_per_user_stats(client, login_as, problem_ids):
    headers = await login_as("a@example.com")
    first, second = problem_ids
    await solve(client, headers, first)
    await solve(client, headers, first)

    problems = (await client.get(f"{BASE}/problems", headers=headers)).json()
    by_id = {p["id"]: p for p in problems}
    assert by_id[first]["solve_count"] == 2
    assert isinstance(by_id[first]["best_seconds"], int)
    assert by_id[second]["solve_count"] == 0
    assert by_id[second]["best_seconds"] is None
    assert by_id[first]["last_solved_at"] is not None
    assert by_id[second]["last_solved_at"] is None


async def test_unfinished_attempts_do_not_count(client, login_as, problem_ids):
    headers = await login_as("a@example.com")
    await client.post(f"{BASE}/problems/{problem_ids[0]}/attempts", headers=headers)
    stats = (await client.get(f"{BASE}/stats", headers=headers)).json()
    assert stats == {
        "solved_problems": 0,
        "total_problems": 2,
        "total_attempts": 0,
        "total_seconds": 0,
    }


async def test_stats_totals(client, login_as, problem_ids):
    headers = await login_as("a@example.com")
    first, second = problem_ids
    await solve(client, headers, first)
    await solve(client, headers, first)
    await solve(client, headers, second)

    stats = (await client.get(f"{BASE}/stats", headers=headers)).json()
    assert stats["solved_problems"] == 2
    assert stats["total_problems"] == 2
    assert stats["total_attempts"] == 3
    assert stats["total_seconds"] >= 0


async def test_stats_are_per_user(client, login_as, problem_ids):
    owner = await login_as("owner@example.com")
    other = await login_as("other@example.com")
    await solve(client, owner, problem_ids[0])

    stats = (await client.get(f"{BASE}/stats", headers=other)).json()
    assert stats["solved_problems"] == 0
    problems = (await client.get(f"{BASE}/problems", headers=other)).json()
    assert all(p["solve_count"] == 0 for p in problems)


async def test_history_on_problem_detail(client, login_as, problem_ids):
    headers = await login_as("a@example.com")
    await solve(client, headers, problem_ids[0])
    await solve(client, headers, problem_ids[0])

    detail = (await client.get(f"{BASE}/problems/{problem_ids[0]}", headers=headers)).json()
    history = detail["history"]
    assert len(history) == 2
    assert all(a["finished_at"] is not None for a in history)
    assert history[0]["finished_at"] >= history[1]["finished_at"]  # newest first