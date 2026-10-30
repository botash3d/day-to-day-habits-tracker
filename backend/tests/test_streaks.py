import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest_asyncio

from app.models.attempt import Attempt
from app.models.problem import Problem
from app.services.streaks import compute_streaks, get_streaks

BASE = "/api/v1/dsa"
TODAY = date(2026, 10, 28)


def days(*days_ago):
    return {TODAY - timedelta(days=n) for n in days_ago}


# ---- Pure streak logic ----

def test_no_activity():
    assert compute_streaks(set(), TODAY) == (0, 0)


def test_streak_including_today():
    assert compute_streaks(days(0, 1, 2), TODAY) == (3, 3)


def test_streak_alive_if_only_yesterday_is_active():
    assert compute_streaks(days(1, 2), TODAY) == (2, 2)


def test_streak_broken_by_a_gap():
    assert compute_streaks(days(2, 3), TODAY) == (0, 2)


def test_longest_streak_can_be_in_the_past():
    assert compute_streaks(days(0, 10, 11, 12, 13), TODAY) == (1, 4)


def test_streak_across_a_month_boundary():
    active = {date(2026, 10, 31), date(2026, 11, 1), date(2026, 11, 2)}
    assert compute_streaks(active, date(2026, 11, 2)) == (3, 3)


# ---- Endpoint and timezone behaviour ----

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


async def solve(client, headers, problem_id):
    attempt = (await client.post(f"{BASE}/problems/{problem_id}/attempts", headers=headers)).json()
    done = await client.post(f"{BASE}/attempts/{attempt['id']}/finish", json={}, headers=headers)
    assert done.status_code == 200


async def test_streaks_require_login(client):
    assert (await client.get(f"{BASE}/streaks")).status_code == 401


async def test_streak_after_solving_today(client, login_as, problem_id):
    headers = await login_as("a@example.com")
    await solve(client, headers, problem_id)

    response = await client.get(f"{BASE}/streaks", params={"tz": "Asia/Kolkata"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["solved_today"] is True
    assert body["current_streak"] == 1
    assert body["longest_streak"] == 1
    assert body["total_active_days"] == 1
    assert len(body["days"]) == 84
    assert body["days"][-1]["date"] == body["today"]
    assert body["days"][-1]["count"] == 1


async def test_invalid_timezone_is_rejected(client, login_as):
    headers = await login_as("a@example.com")
    response = await client.get(f"{BASE}/streaks", params={"tz": "Not/AZone"}, headers=headers)
    assert response.status_code == 422


async def test_streaks_are_per_user(client, login_as, problem_id):
    owner = await login_as("owner@example.com")
    other = await login_as("other@example.com")
    await solve(client, owner, problem_id)

    body = (await client.get(f"{BASE}/streaks", headers=other)).json()
    assert body["current_streak"] == 0
    assert body["total_active_days"] == 0


async def test_days_are_bucketed_in_the_users_timezone(
    client, login_as, session_factory, problem_id
):
    headers = await login_as("tz@example.com")
    user_id = uuid.UUID((await client.get("/api/v1/users/me", headers=headers)).json()["id"])

    # 20:00 UTC on Oct 27 is already 01:30 on Oct 28 in India.
    finished = datetime(2026, 10, 27, 20, 0, tzinfo=UTC)
    now = datetime(2026, 10, 28, 10, 0, tzinfo=UTC)
    async with session_factory() as session:
        session.add(
            Attempt(
                user_id=user_id, problem_id=problem_id,
                started_at=finished - timedelta(minutes=10),
                finished_at=finished, duration_seconds=600,
            )
        )
        await session.commit()
        india = await get_streaks(session, user_id, ZoneInfo("Asia/Kolkata"), now)
        utc = await get_streaks(session, user_id, ZoneInfo("UTC"), now)

    assert india.days[-1].date == date(2026, 10, 28)
    assert india.days[-1].count == 1
    assert utc.days[-1].date == date(2026, 10, 28)
    assert utc.days[-1].count == 0
    assert utc.days[-2].date == date(2026, 10, 27)
    assert utc.days[-2].count == 1