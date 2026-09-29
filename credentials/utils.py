import secrets
from datetime import date, datetime, timedelta

from django.utils import timezone


MAX_RECURRING_SESSIONS = 10


def generate_unique_credential():
    """Return a random 6-digit code unique across all EmployeeCredential records."""
    from .models import EmployeeCredential

    while True:
        code = f"{secrets.randbelow(1_000_000):06d}"
        if not EmployeeCredential.objects.filter(credential=code).exists():
            return code


def format_session_title(series_title: str, starts_at: datetime) -> str:
    """Build per-occurrence title: '{series} — 8 Sep 2026'."""
    base = (series_title or '').strip() or 'Session'
    return f"{base} — {starts_at.day} {starts_at.strftime('%b %Y')}"


def generate_weekly_occurrences(
    starts_at: datetime,
    ends_at: datetime,
    recurrence_end_date: date,
    *,
    max_sessions: int = MAX_RECURRING_SESSIONS,
):
    """
    Yield (occurrence_starts_at, occurrence_ends_at) weekly on the same weekday
    as starts_at, inclusive of recurrence_end_date, capped at max_sessions.
    """
    if ends_at <= starts_at:
        raise ValueError('ends_at must be after starts_at')

    duration = ends_at - starts_at
    first_day = starts_at.date()
    if first_day > recurrence_end_date:
        raise ValueError('recurrence_end_date must be on or after the start date')

    current_start = starts_at
    count = 0
    while current_start.date() <= recurrence_end_date and count < max_sessions:
        yield current_start, current_start + duration
        current_start = current_start + timedelta(weeks=1)
        count += 1


def _shift_months(dt: datetime, months: int) -> datetime:
    """Return dt shifted by `months`, clamped to day 1 of that month at midnight."""
    month_index = (dt.year * 12 + (dt.month - 1)) + months
    year, month0 = divmod(month_index, 12)
    return dt.replace(
        year=year,
        month=month0 + 1,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def cycle_end_from_start(cycle_start: datetime) -> datetime:
    """Return the exclusive cycle end (1st of the following month)."""
    return _shift_months(cycle_start, 1)


def format_cycle_display(cycle_start: datetime, cycle_end: datetime) -> str:
    """Format cycle dates for display. Example: 'Sep 01 - Oct 01, 2026'."""
    start_str = cycle_start.strftime('%b %d')
    end_str = cycle_end.strftime('%b %d, %Y')
    return f'{start_str} - {end_str}'


def get_current_cycle():
    """
    Calculate current payment cycle dates.
    Cycle runs from the 1st of current month to 1st of next month.

    Returns:
        tuple: (cycle_start, cycle_end) as timezone-aware datetime objects
    """
    now = timezone.now()
    cycle_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return cycle_start, cycle_end_from_start(cycle_start)


def get_past_cycles(months_back=6):
    """
    Get list of current and past cycle dates for dropdown.
    Returns tuples of (cycle_start, cycle_end, display_string).
    """
    now = timezone.now()
    cycles = []

    for i in range(months_back + 1):
        cycle_start = _shift_months(now, -i)
        cycle_end = cycle_end_from_start(cycle_start)
        display = format_cycle_display(cycle_start, cycle_end)
        cycles.append((cycle_start, cycle_end, display))

    return cycles
