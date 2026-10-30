from datetime import date

from pydantic import BaseModel


class DayActivity(BaseModel):
    date: date
    count: int


class StreakStats(BaseModel):
    current_streak: int
    longest_streak: int
    total_active_days: int
    solved_today: bool
    today: date
    # The last 84 days (12 weeks), oldest first, including days with no activity.
    days: list[DayActivity]