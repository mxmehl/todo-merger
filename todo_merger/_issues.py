"""Handling issues which come in from different sources"""

import logging
from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from urllib.parse import urlparse

from dateutil import parser
from flask import current_app
from github import AuthenticatedUser, Github, Issue, PaginatedList
from gitlab import Gitlab
from gitlab.base import RESTObject, RESTObjectList


@dataclass
class IssueItem:  # pylint: disable=too-many-instance-attributes
    """Dataclass holding a single issue"""

    updated_at: datetime = field(default_factory=datetime.now)
    updated_at_display: str = ""
    assignee_users: list = field(default_factory=list)
    due_date: str = ""
    epic_title: str = ""
    milestone_title: str = ""
    ref: str = ""
    pull: bool = False
    title: str = ""
    web_url: str = ""
    service: str = ""

    def import_values(self, **kwargs):
        """Import data from a dict"""
        for attr, value in kwargs.items():
            setattr(self, attr, value)


@dataclass
class IssuesStats:  # pylint: disable=too-many-instance-attributes
    """Dataclass holding a stats about all issues"""

    total: int = 0
    gitlab: int = 0
    github: int = 0
    pulls: int = 0
    issues: int = 0
    due_dates_total: int = 0
    milestones_total: int = 0
    epics_total: int = 0


# HELPER FUNCTIONS


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


# API TO IssueItem DATACLASS


def _import_gitlab_issues(
    issues: RESTObjectList | list[RESTObject], myuser: str
) -> list[IssueItem]:
    """Create a list of IssueItem from the GitLab API results"""
    issueitems: list[IssueItem] = []
    for issue in issues:
        d = IssueItem()
        d.import_values(
            updated_at=_convert_to_datetime(issue.updated_at),
            updated_at_display=_time_ago(_convert_to_datetime(issue.updated_at)),
            assignee_users=_sort_assignees(
                [u["username"] for u in issue.assignees if issue.assignees], myuser
            ),
            due_date=issue.due_date if hasattr(issue, "due_date") else "",
            epic_title=(
                issue.epic["title"] if hasattr(issue, "epic") and issue.epic is not None else ""
            ),
            milestone_title=issue.milestone["title"] if issue.milestone else "",
            ref=issue.references["full"],
            title=issue.title,
            web_url=issue.web_url,
            pull=hasattr(issue, "merge_status"),
            service="gitlab",
        )
        issueitems.append(d)

    return issueitems


def _import_github_issues(
    issues: PaginatedList.PaginatedList[Issue.Issue], myuser: str
) -> list[IssueItem]:
    """Create a list of IssueItem from the GitHub API results"""
    issueitems: list[IssueItem] = []
    for issue in issues:
        d = IssueItem()
        d.import_values(
            updated_at=_convert_to_datetime(issue.updated_at),
            updated_at_display=_time_ago(_convert_to_datetime(issue.updated_at)),
            assignee_users=_sort_assignees(
                [u.login for u in issue.assignees if issue.assignees], myuser
            ),
            due_date="",
            epic_title="",
            milestone_title=issue.milestone.title if issue.milestone else "",
            ref=_gh_url_to_ref(issue.html_url),
            title=issue.title,
            web_url=issue.html_url,
            pull=issue.pull_request is not None,
            service="github",
        )
        issueitems.append(d)

    return issueitems


# GET ISSUES FROM SERVICES


def gitlab_get_issues(gitlab: Gitlab) -> list[IssueItem]:
    """Get all issues assigned to authenticated user"""
    issues: list[IssueItem] = []
    myuser: str = gitlab.user.username  # type: ignore

    # See https://docs.gitlab.com/ee/api/issues.html
    assigned_issues = gitlab.issues.list(
        assignee_username=myuser, state="opened", scope="all"  # type: ignore
    )
    # See https://docs.github.com/en/rest/search/search
    review_requests = gitlab.mergerequests.list(
        reviewer_username=myuser, state="opened", scope="all"
    )

    issues.extend(_import_gitlab_issues(issues=assigned_issues, myuser=myuser))
    issues.extend(_import_gitlab_issues(issues=review_requests, myuser=myuser))

    return issues


def github_get_issues(github: Github) -> list[IssueItem]:
    """Get all issues assigned to authenticated user"""
    issues: list[IssueItem] = []
    myuser: AuthenticatedUser.AuthenticatedUser = github.get_user()  # type: ignore

    # See https://docs.github.com/en/rest/issues/issues
    assigned_issues = myuser.get_issues()
    # See https://docs.github.com/en/rest/search/search
    review_requests = github.search_issues(
        query=f"is:open is:pr archived:false review-requested:{myuser.login}"
    )

    issues.extend(_import_github_issues(issues=assigned_issues, myuser=myuser.login))
    issues.extend(_import_github_issues(issues=review_requests, myuser=myuser.login))

    return issues


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

    return issues


# ISSUE PRIORIZATION


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


# STATS ABOUT FETCHED ISSUES


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
