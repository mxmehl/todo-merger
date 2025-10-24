"""GitLab issue fetching functions"""

import hashlib
from typing import Any

from gitlab import Gitlab

from ._helpers import convert_to_datetime, sort_assignees
from ._types import IssueItem


def _import_gitlab_issues(issues: list[Any], myuser: str, instance_id: str) -> list[IssueItem]:
    """Create a list of IssueItem from the GitLab API results"""
    issueitems: list[IssueItem] = []
    for issue in issues:
        d = IssueItem()
        d.import_values(
            assignee_users=sort_assignees(
                [u["username"] for u in issue.assignees if issue.assignees], myuser
            ),
            due_date=issue.due_date if hasattr(issue, "due_date") else "",
            epic_title=(
                issue.epic["title"] if hasattr(issue, "epic") and issue.epic is not None else ""
            ),
            labels=issue.labels,
            milestone_title=issue.milestone["title"] if issue.milestone else "",
            pull=hasattr(issue, "merge_status"),
            ref=issue.references["full"],
            service="gitlab",
            title=issue.title,
            uid=f"gitlab-{instance_id}-{issue.id}",
            updated_at=convert_to_datetime(issue.updated_at),
            web_url=issue.web_url,
        )
        d.fill_remaining_fields()
        issueitems.append(d)

    return issueitems


def gitlab_get_issues(gitlab: Gitlab) -> list[IssueItem]:
    """Get all issues assigned to authenticated user"""
    issues: list[IssueItem] = []
    myuser: str = gitlab.user.username  # type: ignore
    # Create a unique enough id for the GitLab instance in case we have more
    # than one. Avoids issue id collisions
    instance_id = hashlib.md5(gitlab.url.encode()).hexdigest()[:6]

    # See https://docs.gitlab.com/ee/api/issues.html
    assigned_issues = gitlab.issues.list(
        assignee_username=myuser, state="opened", scope="all", get_all=True
    )
    # See https://docs.gitlab.com/ee/api/merge_requests.html
    merge_requests_assigned = gitlab.mergerequests.list(
        assignee_username=myuser, state="opened", scope="all", get_all=True
    )
    merge_requests_reviews = gitlab.mergerequests.list(
        reviewer_username=myuser, state="opened", scope="all", get_all=True
    )

    issues.extend(
        _import_gitlab_issues(issues=assigned_issues, myuser=myuser, instance_id=instance_id)
    )
    issues.extend(
        _import_gitlab_issues(
            issues=merge_requests_assigned, myuser=myuser, instance_id=instance_id
        )
    )
    issues.extend(
        _import_gitlab_issues(issues=merge_requests_reviews, myuser=myuser, instance_id=instance_id)
    )

    return issues
