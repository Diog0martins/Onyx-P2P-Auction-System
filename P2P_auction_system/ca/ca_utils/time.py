from datetime import datetime, timedelta, timezone

# Introduz time-stamps
def now_iso() -> str:
    """Returns the current UTC time formatted as an ISO 8601 string."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

# Introduz time-stamps
def iso_in_days(days: int) -> str:
    """Returns a calculated future UTC date (current time + days) as an ISO 8601 string."""
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()
