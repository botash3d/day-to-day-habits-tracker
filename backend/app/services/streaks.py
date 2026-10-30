import uuid
from collections import Counter
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempt import Attempt
from app.schemas.streak import DayActivity, StreakStats

WINDOW_DAYS = 84


def compute_streaks(active_days: set[date], today: date) -> tuple[int, int]:
    """Return (current_streak, longest_streak) for a set of active calendar days."""
    if not active_days:
        return 0, 0

    longest = 0
    run = 0
    previous: date | None = None
    for day in sorted(active_days):
        if previous is not None and day - previous == timedelta(days=1):
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        previous = day

    # The streak is still alive if you solved something today or yesterday.
    anchor = today if today in active_days else today - timedelta(days=1)
    current = 0
    day = anchor
    while day in active_days:
        current += 1
        day -= timedelta(days=1)
    return current, longest


def _to_utc(value: datetime) -> datetime:
    # SQLite returns naive datetimes; PostgreSQL returns aware ones.
    return value if value.tzinfo else value.replace(tzinfo=UTC)


async def get_streaks(
    session: AsyncSession,
    user_id: uuid.UUID,
    tz: ZoneInfo,
    now: datetime | None = None,
) -> StreakStats:
    now = now or datetime.now(UTC)
    today = now.astimezone(tz).date()

    finished_times = await session.scalars(
        select(Attempt.finished_at).where(
            Attempt.user_id == user_id, Attempt.finished_at.is_not(None)
        )
    )
    counts = Counter(_to_utc(ts).astimezone(tz).date() for ts in finished_times)

    current, longest = compute_streaks(set(counts), today)
    window = [today - timedelta(days=i) for i in range(WINDOW_DAYS - 1, -1, -1)]
    return StreakStats(
        current_streak=current,
        longest_streak=longest,
        total_active_days=len(counts),
        solved_today=counts.get(today, 0) > 0,
        today=today,
        days=[DayActivity(date=d, count=counts.get(d, 0)) for d in window],
    )