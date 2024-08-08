"""Handling issues which come in from different sources"""

import logging
from dataclasses import dataclass, field, fields
from urllib.parse import urlparse

from flask import current_app
from github import AuthenticatedUser, Github
from gitlab import Gitlab


@dataclass
class IssueItem:  # pylint: disable=too-many-instance-attributes
    """Dataclass holding a single issue"""

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


def gitlab_get_issues(gitlab: Gitlab) -> list[IssueItem]:
    """Get all issues assigned to authenticated user"""
    issues: list[IssueItem] = []
    myuser: str = gitlab.user.username  # type: ignore
    for issue in gitlab.issues.list(
        assignee_username=myuser, state="opened", scope="all"  # type: ignore
    ):
        # See https://docs.gitlab.com/ee/api/issues.html
        d = IssueItem()
        d.import_values(
            assignee_users=_sort_assignees(
                [u["username"] for u in issue.assignees if issue.assignees], myuser
            ),
            due_date=issue.due_date,
            epic_title=issue.epic["title"] if issue.epic else "",
            milestone_title=issue.milestone["title"] if issue.milestone else "",
            ref=issue.references["full"],
            title=issue.title,
            web_url=issue.web_url,
            service="gitlab",
        )
        issues.append(d)

    return issues


def _gh_url_to_ref(url: str):
    """Convert a GitHub issue URL to a ref"""
    url = urlparse(url).path
    url = url.strip("/")

    # Run replacements
    replacements = {"/issues/": "#", "/pull/": "#"}
    for search, replacement in replacements.items():
        url = url.replace(search, replacement)

    return url


def github_get_issues(github: Github) -> list[IssueItem]:
    """Get all issues assigned to authenticated user"""
    issues: list[IssueItem] = []
    myuser: AuthenticatedUser.AuthenticatedUser = github.get_user()  # type: ignore

    # See https://docs.github.com/en/rest/issues/issues
    assigned_issues = myuser.get_issues()
    # See https://docs.github.com/en/rest/search/search
    reviews_requests = github.search_issues(
        query=f"is:open is:pr archived:false review-requested:{myuser.login}"
    )

    for issue in list(assigned_issues) + list(reviews_requests):

        d = IssueItem()
        d.import_values(
            assignee_users=_sort_assignees(
                [u.login for u in issue.assignees if issue.assignees], myuser.login
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
        issues.append(d)

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


def _replace_none_with_empty_string(obj: IssueItem) -> IssueItem:
    """Replace None values of a dataclass with an empty string. Makes sorting
    easier"""
    for f in fields(obj):
        value = getattr(obj, f.name)
        if value is None:
            setattr(obj, f.name, "")

    return obj


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
        sort_by = [("due_date", False), ("milestone_title", True)]

    logging.info("Sort issues based on %s", sort_by)

    # Replace None with empty string in all tasks
    issues = [_replace_none_with_empty_string(task) for task in issues]

    def sort_key(issue: IssueItem) -> tuple:
        # Create a tuple of the field values to sort by, considering the reverse order
        key: list[tuple[int, str | None]] = []
        for f, reverse in sort_by:
            value: str = getattr(issue, f).lower()
            is_empty = value == ""
            # Place empty values at the end
            if is_empty:
                key.append((1, None))  # `1` indicates an empty value
            else:
                if reverse:
                    value = "".join(chr(255 - ord(char)) for char in value)
                key.append((0, value))  # `0` indicates a non-empty value
        return tuple(key)

    return sorted(issues, key=sort_key)
