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
def get_current_cycle():
    """
    Calculate current payment cycle dates.
    Cycle runs from the 1st of current month to 1st of next month.
    Example: Sept 1 2026 to Oct 1 2026, Oct 1 2026 to Nov 1 2026, etc.
    
    Returns:
        tuple: (cycle_start, cycle_end) as datetime objects
    """
    now = datetime.now()
    
    # Cycle starts on 1st of current month at midnight
    cycle_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Cycle ends on 1st of next month at midnight
    if cycle_start.month == 12:
        cycle_end = cycle_start.replace(year=cycle_start.year + 1, month=1)
    else:
        cycle_end = cycle_start.replace(month=cycle_start.month + 1)
    
    return cycle_start, cycle_end


def get_cycle_display():
    """
    Get human-readable cycle dates for display.
    Example: "Sept 1 - Oct 1, 2026"
    
    Returns:
        str: Formatted cycle date range
    """
    cycle_start, cycle_end = get_current_cycle()
    
    # Format: "Sept 1 - Oct 1, 2026"
    start_str = cycle_start.strftime("%b %d")
    end_str = cycle_end.strftime("%b %d, %Y")
    
    return f"{start_str} - {end_str}"


def get_past_cycles(months_back=6):
    """
    Get list of past cycle dates for dropdown.
    Returns tuples of (cycle_start, cycle_end, display_string).
    
    Args:
        months_back: How many months back to show (default 6)
    
    Returns:
        list: [(start, end, display_string), ...]
    """
    cycles = []
    now = datetime.now()
    
    # Get current and past cycles
    for i in range(months_back + 1):
        # Go back i months
        if now.month - i > 0:
            cycle_start = now.replace(
                year=now.year,
                month=now.month - i,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
        else:
            cycle_start = now.replace(
                year=now.year - 1,
                month=12 + (now.month - i),
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0
            )
        
        # Cycle end is 1st of next month
        if cycle_start.month == 12:
            cycle_end = cycle_start.replace(year=cycle_start.year + 1, month=1)
        else:
            cycle_end = cycle_start.replace(month=cycle_start.month + 1)
        
        # Format display
        start_str = cycle_start.strftime("%b %d")
        end_str = cycle_end.strftime("%b %d, %Y")
        display = f"{start_str} - {end_str}"
        
        cycles.append((cycle_start, cycle_end, display))
    
    return cycles