from datetime import datetime, timedelta, timezone

# Introduz time-stamps
def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

# Introduz time-stamps
def iso_in_days(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).replace(microsecond=0).isoformat()
