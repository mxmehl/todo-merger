"""Gitea API client and issue fetching functions."""

import hashlib
import logging

import httpx

from ._helpers import convert_to_datetime, sort_assignees
from ._types import IssueItem


class Gitea:
    """Simple Gitea API client wrapping the endpoints needed by todo-merger."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self._client = httpx.Client(
            base_url=f"{self.url}/api/v1",
            headers={"Authorization": f"token {token}", "Accept": "application/json"},
            timeout=10,
        )
        self.user: dict[str, str | int | bool] = self._get("/user")
        logging.info("Logged into Gitea as %s on %s", self.user["login"], self.url)

    def _get(self, path: str, params: dict | None = None) -> dict:
        """GET request."""
        resp = self._client.request("GET", path, params=params)
        resp.raise_for_status()
        return resp.json()

    def _get_all(self, path: str, params: dict | None = None) -> list[dict]:
        """GET all pages of a paginated endpoint."""
        params = params or {}
        params.setdefault("limit", 50)
        params["page"] = 1
        results: list[dict] = []
        while True:
            resp = self._client.request("GET", path, params=params)
            resp.raise_for_status()
            page: list[dict] = resp.json()
            if not page:
                break
            results.extend(page)
            if len(page) < params["limit"]:
                break
            params["page"] += 1
        return results

    def _post(self, path: str, json: dict | None = None) -> dict:
        """POST request."""
        resp = self._client.request("POST", path, json=json)
        resp.raise_for_status()
        return resp.json()

    def search_issues(
        self, *, assigned: bool = False, review_requested: bool = False, state: str = "open"
    ) -> list[dict]:
        """Search issues across all repos the user has access to."""
        params: dict[str, str | bool | int] = {"state": state}
        if assigned:
            params["assigned"] = True
        if review_requested:
            params["review_requested"] = True
        return self._get_all("/repos/issues/search", params=params)

    def get_repo_labels(self, owner: str, repo: str) -> list[dict]:
        """Get all labels for a repository."""
        return self._get_all(f"/repos/{owner}/{repo}/labels")

    def create_issue(
        self, owner: str, repo: str, *, title: str, labels: list[int], assignee: str
    ) -> dict:
        """Create an issue in a repository."""
        return self._post(
            f"/repos/{owner}/{repo}/issues",
            json={"title": title, "labels": labels, "assignee": assignee},
        )


def _import_gitea_issues(issues: list[dict], myuser: str, instance_id: str) -> list[IssueItem]:
    """Create a list of IssueItem from the Gitea API results."""
    issueitems: list[IssueItem] = []
    for issue in issues:
        repo_meta = issue.get("repository", {})
        ref = f"{repo_meta.get('full_name', '')}#{issue['number']}"

        d = IssueItem()
        d.import_values(
            assignee_users=sort_assignees(
                [u["login"] for u in (issue.get("assignees") or [])], myuser
            ),
            due_date=issue.get("due_date", "")[:10] if issue.get("due_date") else "",
            epic_title="",
            labels=[label["name"] for label in (issue.get("labels") or [])],
            milestone_title=issue["milestone"]["title"] if issue.get("milestone") else "",
            pull=issue.get("pull_request") is not None,
            ref=ref,
            service="gitea",
            title=issue["title"],
            uid=f"gitea-{instance_id}-{issue['id']}",
            updated_at=convert_to_datetime(issue["updated_at"]),
            web_url=issue["html_url"],
        )
        d.fill_remaining_fields()
        issueitems.append(d)

    return issueitems


def gitea_get_issues(gitea: Gitea) -> list[IssueItem]:
    """Get all issues and PRs assigned to authenticated user."""
    issues: list[IssueItem] = []
    myuser = str(gitea.user["login"])
    instance_id = hashlib.md5(gitea.url.encode(), usedforsecurity=False).hexdigest()[:6]

    assigned = gitea.search_issues(assigned=True, state="open")
    review_requested = gitea.search_issues(review_requested=True, state="open")

    issues.extend(_import_gitea_issues(assigned, myuser, instance_id))
    issues.extend(_import_gitea_issues(review_requested, myuser, instance_id))

    return issues
