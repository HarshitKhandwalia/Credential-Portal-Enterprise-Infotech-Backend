import secrets
from datetime import date, datetime, timedelta


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
