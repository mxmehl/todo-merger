"""GitHub issue fetching functions."""

from collections.abc import Iterable
from typing import cast
from urllib.parse import urlparse

from github import AuthenticatedUser, Github, Issue

from ._helpers import convert_to_datetime, sort_assignees
from ._types import IssueItem


def _gh_url_to_ref(url: str) -> str:
    """Convert a GitHub issue URL to a ref."""
    url = urlparse(url).path
    url = url.strip("/")

    # Run replacements
    replacements = {"/issues/": "#", "/pull/": "#"}
    for search, replacement in replacements.items():
        url = url.replace(search, replacement)

    return url


def _import_github_issues(
    issues: Iterable[Issue.Issue],
    myuser: str,
) -> list[IssueItem]:
    """Create a list of IssueItem from the GitHub API results."""
    issueitems: list[IssueItem] = []
    for issue in issues:
        d = IssueItem()
        d.import_values(
            assignee_users=sort_assignees(
                [u.login for u in issue.assignees if issue.assignees], myuser
            ),
            due_date="",
            epic_title="",
            labels=[label.name for label in issue.labels],
            milestone_title=issue.milestone.title if issue.milestone else "",
            # Ugly fix to make loading of whether it's a PR faster.
            # `issue.pull_request` would trigger another API call
            pull="/pull/" in issue.html_url,
            ref=_gh_url_to_ref(issue.html_url),
            service="github",
            title=issue.title,
            uid=f"github-{issue.id}",
            updated_at=convert_to_datetime(issue.updated_at),
            web_url=issue.html_url,
        )
        d.fill_remaining_fields()
        issueitems.append(d)

    return issueitems


def github_get_issues(github: Github) -> list[IssueItem]:
    """Get all issues assigned to authenticated user."""
    issues: list[IssueItem] = []
    myuser = cast("AuthenticatedUser.AuthenticatedUser", github.get_user())

    # See https://docs.github.com/en/rest/issues/issues
    assigned_issues = myuser.get_issues()
    # See https://docs.github.com/en/rest/search/search
    review_requests = github.search_issues(
        query=f"is:open is:pr archived:false review-requested:{myuser.login}"
    )

    issues.extend(_import_github_issues(issues=assigned_issues, myuser=myuser.login))
    issues.extend(_import_github_issues(issues=review_requests, myuser=myuser.login))

    return issues
