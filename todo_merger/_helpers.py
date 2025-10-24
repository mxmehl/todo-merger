"""Helper functions"""

from datetime import datetime, timezone

from dateutil import parser


def sort_assignees(assignees: list, my_user_name: str) -> str:
    """Provide a human-readable list of assigned users, treating yourself special"""

    # Remove my user name from assignees list, if present
    try:
        assignees.remove(my_user_name)
    except ValueError:
        pass

    # If executing user is the only assignee, there is no use in that field
    if not assignees:
        return ""

    return f"{', '.join(['Me'] + assignees)}"


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
            raise ValueError(f"Unrecognized timestamp format: {timestamp}") from exc

    # If the datetime object is naive (no timezone), assume UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def time_ago(dt):
    """Convert a datetime to a human-readable 'time ago' format"""
    now = datetime.now(timezone.utc)
    diff = now - dt

    if diff.days >= 365:
        years = diff.days // 365
        display = f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days >= 30:
        months = diff.days // 30
        display = f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days >= 7:
        weeks = diff.days // 7
        display = f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif diff.days > 0:
        display = f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        display = f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        display = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        display = "Just now"

    return display
