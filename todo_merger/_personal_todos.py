"""Functions for dealing with a the personal ToDo repo"""

from flask import current_app
from gitlab import Gitlab


def get_personal_todos_service_from_config():
    """Get the service object from the app config"""
    configured_todo_service = current_app.config["todo_repo"]["service"]
    return current_app.config["services"][configured_todo_service][1]


def todo_repo_get_gitlab_labels() -> dict[str, str]:
    """Get all labels from a GitLab repository"""
    gitlab: Gitlab = get_personal_todos_service_from_config()

    personal_repo = current_app.config["todo_repo"]["repo"]

    all_labels = gitlab.projects.get(personal_repo).labels.list(get_all=True)

    # Return dict of label name and label color
    return {label.name: label.color for label in all_labels}


def todo_repo_create_gitlab_issue(title: str, labels: list[str]) -> str:
    """Create a new issue in the personal todo repository (GitLab). Returns the
    web URL of the new issue"""
    gitlab: Gitlab = get_personal_todos_service_from_config()
    user_id = gitlab.user.id  # type: ignore

    personal_repo = current_app.config["todo_repo"]["repo"]

    # Create issue
    result = gitlab.projects.get(personal_repo).issues.create(
        {"title": title, "labels": labels, "assignee_id": user_id}
    )

    return result.web_url
