"""Functions for dealing with a the personal ToDo repo"""

from flask import current_app
from github import Github
from gitlab import Gitlab


def todo_repo_get_gitlab_labels(gitlab: Gitlab) -> dict[str, str]:
    """Get all labels from a GitLab repository"""
    personal_repo = current_app.config["todo_repo"]["repo"]

    all_labels = gitlab.projects.get(personal_repo).labels.list(get_all=True)

    # Return dict of label name and label color
    return {label.name: label.color for label in all_labels}


def todo_repo_create_gitlab_issue(gitlab: Gitlab, title: str, labels: list[str]) -> str:
    """Create a new issue in the personal todo repository (GitLab). Returns the
    web URL of the new issue"""
    user_id = gitlab.user.id  # type: ignore

    personal_repo = current_app.config["todo_repo"]["repo"]

    # Create issue
    result = gitlab.projects.get(personal_repo).issues.create(
        {"title": title, "labels": labels, "assignee_id": user_id}
    )

    return result.web_url
