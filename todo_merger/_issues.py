"""Handling issues which come in from different sources"""

import logging
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from urllib.parse import urlparse

from dateutil import parser
from flask import current_app

from todo_merger._github import github_get_issues
from todo_merger._gitlab import gitlab_get_issues
from todo_merger._msplanner import msplannerfile_get_issues

ISSUE_RANKING_TABLE = {"pin": -1, "high": 1, "normal": 5, "low": 99}


@dataclass
class IssueItem:  # pylint: disable=too-many-instance-attributes
    """Dataclass holding a single issue"""

    assignee_users: list = field(default_factory=list)
    due_date: str = ""
    epic_title: str = ""
    labels: list = field(default_factory=list)
    milestone_title: str = ""
    pull: bool = False
    rank: int = ISSUE_RANKING_TABLE["normal"]
    ref: str = ""
    service: str = ""
    title: str = ""
    todolist: bool = False
    uid: str = ""
    updated_at_display: str = ""
    updated_at: datetime = field(default_factory=datetime.now)
    web_url: str = ""

    def import_values(self, **kwargs):
        """Import data from a dict"""
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    def fill_remaining_fields(self):
        """Fill remaining fields that have not been imported directly and which
        are solely derived from attribute values"""
        # updated_at_display
        self.updated_at_display = _time_ago(_convert_to_datetime(self.updated_at))

    def convert_to_dict(self):
        """Return the current dataclass as dict"""
        return asdict(self)


@dataclass
class IssuesStats:  # pylint: disable=too-many-instance-attributes
    """Dataclass holding a stats about all issues"""

    total: int = 0
    gitlab: int = 0
    github: int = 0
    msplanner: int = 0
    pulls: int = 0
    issues: int = 0
    due_dates_total: int = 0
    milestones_total: int = 0
    epics_total: int = 0


# ----------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------


def _sort_assignees(assignees: list, my_user_name: str) -> str:
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


def _gh_url_to_ref(url: str):
    """Convert a GitHub issue URL to a ref"""
    url = urlparse(url).path
    url = url.strip("/")

    # Run replacements
    replacements = {"/issues/": "#", "/pull/": "#"}
    for search, replacement in replacements.items():
        url = url.replace(search, replacement)

    return url


def _replace_none_with_empty_string(obj: IssueItem) -> IssueItem:
    """Replace None values of a dataclass with an empty string. Makes sorting
    easier"""
    for f in fields(obj):
        value = getattr(obj, f.name)
        if value is None:
            setattr(obj, f.name, "")

    return obj


def _convert_to_datetime(timestamp: str | datetime) -> datetime:
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


def _time_ago(dt):
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


# ----------------------------------------
# ISSUES FETCHING FROM ALL SERVICES
# ----------------------------------------


def get_all_issues() -> list[IssueItem]:
    """Get all issues from the supported services"""
    issues: list[IssueItem] = []
    for name, service in current_app.config["services"].items():
        if service[0] == "github":
            logging.info("Getting assigned GitHub issues for %s", name)
            issues.extend(github_get_issues(service[1]))
        elif service[0] == "gitlab":
            logging.info("Getting assigned GitLab issues for %s", name)
            issues.extend(gitlab_get_issues(service[1]))
        elif service[0] == "msplanner-file":
            logging.info("Getting assigned MS Planner tasks for %s", name)
            issues.extend(msplannerfile_get_issues(service[1]))
        else:
            print(f"Service {service[0]} not supported for fetching issues")

    return issues


# ----------------------------------------
# ISSUE PRIORIZATION AND FILTERING
# ----------------------------------------


def prioritize_issues(
    issues: list[IssueItem], sort_by: list[tuple[str, bool]] | None = None
) -> list[IssueItem]:
    """
    Sorts the list of IssueItem objects based on multiple criteria.

    :param issues: List of IssueItem objects to sort.

    :param sort_by: List of tuples where each tuple contains:
                    - field name to sort by as a string
                    - a boolean indicating whether to sort in reverse order
                      (True for descending, False for ascending)

    :return: Sorted list of IssueItem objects.
    """
    if sort_by is None:
        sort_by = [
            ("due_date", False),
            ("milestone_title", True),
            ("epic_title", True),
            ("updated_at", True),
        ]

    logging.info("Sort issues based on %s", sort_by)

    # Replace None with empty string in all tasks
    issues = [_replace_none_with_empty_string(task) for task in issues]

    def sort_key(issue: IssueItem) -> tuple:
        # Create a tuple of the field values to sort by, considering the reverse order
        key: list[tuple[int, str | None]] = []
        for f, reverse in sort_by:
            value: str | datetime = getattr(issue, f)
            # Convert datetime to str
            if isinstance(value, datetime):
                value = value.strftime("%s")
            elif isinstance(value, str):
                value = value.lower()
            is_empty: bool = value == ""
            # Place empty values at the end
            if is_empty:
                key.append((1, None))  # `1` indicates an empty value
            else:
                if reverse:
                    value = "".join(chr(255 - ord(char)) for char in value)
                key.append((0, value))  # `0` indicates a non-empty value
        return tuple(key)

    return sorted(issues, key=sort_key)


def apply_user_issue_config(
    issues: list[IssueItem], issue_config_dict: dict[str, dict[str, int | bool]]
) -> list[IssueItem]:
    """Apply local user configuration to issues"""
    for issue in issues:
        if issue.uid in issue_config_dict:
            issue.rank = issue_config_dict[issue.uid].get("rank", ISSUE_RANKING_TABLE["normal"])
            logging.debug("Applied rank %s to issue %s (%s)", issue.rank, issue.uid, issue.title)
            if issue_config_dict[issue.uid].get("todolist", False):
                logging.debug("Put issue %s on todo list (%s)", issue.uid, issue.title)
                issue.todolist = True

    return issues


def apply_issue_filter(issues: list[IssueItem], issue_filter: str | None) -> list[IssueItem]:
    """Apply issue filter to issues"""
    if not issue_filter:
        logging.debug("No issue filter applied")

    logging.info("Applying issue filter '%s'", issue_filter)

    if issue_filter == "todolist":
        issues = [issue for issue in issues if issue.todolist]

    return issues


# ----------------------------------------
# STATS ABOUT FETCHED ISSUES
# ----------------------------------------


def get_issues_stats(issues: list[IssueItem]) -> IssuesStats:
    """Create some stats about the collected issues"""
    stats = IssuesStats()

    for issue in issues:
        # Total issues
        stats.total += 1
        # Services total
        setattr(stats, issue.service, getattr(stats, issue.service) + 1)
        # Issue/PR counter
        if issue.pull:
            stats.pulls += 1
        else:
            stats.issues += 1
        # Number of due dates, milestones, and epics
        stats.due_dates_total += 1 if issue.due_date else 0
        stats.milestones_total += 1 if issue.milestone_title else 0
        stats.epics_total += 1 if issue.epic_title else 0

    return stats
