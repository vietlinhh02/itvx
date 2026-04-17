"""Shared datetime helpers for Vietnam time serialization."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

VIETNAM_TIME_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")
VIETNAM_TIME_ZONE_NAME = "Asia/Ho_Chi_Minh"


def assume_utc(datetime_value: datetime) -> datetime:
    """Return a timezone-aware UTC datetime from naive-or-aware input."""
    if datetime_value.tzinfo is None:
        return datetime_value.replace(tzinfo=UTC)
    return datetime_value.astimezone(UTC)


def to_vietnam_datetime(datetime_value: datetime) -> datetime:
    """Convert a naive-UTC or aware datetime to Vietnam time."""
    return assume_utc(datetime_value).astimezone(VIETNAM_TIME_ZONE)


def to_vietnam_isoformat(datetime_value: datetime | None) -> str | None:
    """Serialize a datetime for user-facing APIs in Vietnam time."""
    if datetime_value is None:
        return None
    return to_vietnam_datetime(datetime_value).isoformat()


def vietnam_now_isoformat() -> str:
    """Return the current Vietnam time as an ISO 8601 string."""
    return datetime.now(UTC).astimezone(VIETNAM_TIME_ZONE).isoformat()


def parse_client_datetime_to_utc(datetime_value: str) -> datetime:
    """Parse an ISO datetime from the client and normalize it to UTC."""
    parsed = datetime.fromisoformat(datetime_value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=VIETNAM_TIME_ZONE)
    return parsed.astimezone(UTC)
