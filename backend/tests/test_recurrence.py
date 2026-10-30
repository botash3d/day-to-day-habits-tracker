from datetime import date

from app.services.recurrence import next_due_date


def test_daily_on_time():
    assert next_due_date(date(2026, 10, 28), "daily", date(2026, 10, 28)) == date(2026, 10, 29)


def test_daily_overdue_skips_to_after_today():
    assert next_due_date(date(2026, 10, 20), "daily", date(2026, 10, 28)) == date(2026, 10, 29)


def test_completed_early_still_moves_one_step():
    assert next_due_date(date(2026, 11, 5), "daily", date(2026, 10, 28)) == date(2026, 11, 6)


def test_weekly_keeps_the_weekday():
    # Monday 19 Oct, completed on Wednesday 28 Oct -> next Monday is 2 Nov.
    assert next_due_date(date(2026, 10, 19), "weekly", date(2026, 10, 28)) == date(2026, 11, 2)


def test_monthly_clamps_short_months():
    assert next_due_date(date(2026, 1, 31), "monthly", date(2026, 1, 31)) == date(2026, 2, 28)


def test_monthly_restores_the_long_day_when_possible():
    assert next_due_date(date(2026, 1, 31), "monthly", date(2026, 2, 28)) == date(2026, 3, 31)


def test_monthly_across_the_year_end():
    assert next_due_date(date(2026, 12, 15), "monthly", date(2026, 12, 15)) == date(2027, 1, 15)


def test_monthly_leap_year():
    assert next_due_date(date(2028, 1, 31), "monthly", date(2028, 1, 31)) == date(2028, 2, 29)