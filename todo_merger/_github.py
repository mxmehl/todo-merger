"""GitHub issue fetching functions"""

from typing import Any

from github import AuthenticatedUser, Github, Issue, PaginatedList

from ._issues import IssueItem, _convert_to_datetime, _gh_url_to_ref, _sort_assignees


def _import_github_issues(
    issues: PaginatedList.PaginatedList[Issue.Issue] | Any, myuser: str
) -> list[IssueItem]:
    """Create a list of IssueItem from the GitHub API results"""
    issueitems: list[IssueItem] = []
    for issue in issues:
        d = IssueItem()
        d.import_values(
            assignee_users=_sort_assignees(
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
            updated_at=_convert_to_datetime(issue.updated_at),
            web_url=issue.html_url,
        )
        d.fill_remaining_fields()
        issueitems.append(d)

    return issueitems


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
