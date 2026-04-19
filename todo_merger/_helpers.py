"""Helper functions."""

import contextlib
from datetime import datetime, timezone

from dateutil import parser


def sort_assignees(assignees: list, my_user_name: str) -> str:
    """Provide a human-readable list of assigned users, treating yourself special."""
    # Remove my user name from assignees list, if present
    with contextlib.suppress(ValueError):
        assignees.remove(my_user_name)

    # If executing user is the only assignee, there is no use in that field
    if not assignees:
        return ""

    return f"{', '.join(['Me', *assignees])}"


def convert_to_datetime(timestamp: str | datetime) -> datetime:
    """
    Convert a timestamp string or datetime to a timezone-aware datetime object.

    Args:
        timestamp (str | datetime): The timestamp string to convert, or the
        datetime object to pass through

    Returns:
        datetime: A timezone-aware datetime object in UTC.
    """
    # Handle if timestamp is already datetime object
    if isinstance(timestamp, datetime):
        dt = timestamp
    # Convert str to datetime
    else:
        try:
            # Attempt to parse with dateutil parser
            dt = parser.isoparse(timestamp)

        except ValueError as exc:
            msg = f"Unrecognized timestamp format: {timestamp}"
            raise ValueError(msg) from exc

    # If the datetime object is naive (no timezone), assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


_DAYS_IN_YEAR = 365
_DAYS_IN_MONTH = 30
_DAYS_IN_WEEK = 7
_SECONDS_IN_HOUR = 3600
_SECONDS_IN_MINUTE = 60


def time_ago(dt: datetime) -> str:
    """Convert a datetime to a human-readable 'time ago' format."""
    now = datetime.now(timezone.utc)
    diff = now - dt

    if diff.days >= _DAYS_IN_YEAR:
        years = diff.days // _DAYS_IN_YEAR
        display = f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days >= _DAYS_IN_MONTH:
        months = diff.days // _DAYS_IN_MONTH
        display = f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days >= _DAYS_IN_WEEK:
        weeks = diff.days // _DAYS_IN_WEEK
        display = f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif diff.days > 0:
        display = f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= _SECONDS_IN_HOUR:
        hours = diff.seconds // _SECONDS_IN_HOUR
        display = f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= _SECONDS_IN_MINUTE:
        minutes = diff.seconds // _SECONDS_IN_MINUTE
        display = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        display = "Just now"

    return display
