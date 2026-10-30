import calendar
from datetime import date, timedelta


def _add_months(value: date, months: int) -> date:
    index = value.month - 1 + months
    year = value.year + index // 12
    month = index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _shift(due: date, repeat: str, steps: int) -> date:
    if repeat == "daily":
        return due + timedelta(days=steps)
    if repeat == "weekly":
        return due + timedelta(weeks=steps)
    if repeat == "monthly":
        return _add_months(due, steps)
    raise ValueError(f"Unsupported repeat: {repeat}")


def next_due_date(due: date, repeat: str, today: date) -> date:
    """First occurrence of the schedule that falls after both the due date and today."""
    steps = 1
    while True:
        candidate = _shift(due, repeat, steps)
        if candidate > today:
            return candidate
        steps += 1