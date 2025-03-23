from datetime import datetime, timezone

def utcnow():
    """Get the current UTC time."""
    return datetime.now(timezone.utc)

def naive_utcnow():
    """Get the current UTC time in naive datetime format."""
    return datetime.now(timezone.utc).replace(tzinfo=None)