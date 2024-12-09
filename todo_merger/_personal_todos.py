"""Functions for dealing with a the personal ToDo repo"""

from flask import current_app
from gitlab import Gitlab
from gitlab.base import RESTObject


def get_personal_todos_service_from_config():
    """Get the service object from the app config"""
    configured_todo_service = current_app.config["todo_repo"]["service"]
    return current_app.config["services"][configured_todo_service][1]


def todo_repo_get_gitlab_labels() -> dict[str, str]:
    """Get all labels from a GitLab repository"""
    gitlab: Gitlab = get_personal_todos_service_from_config()

    personal_repo = current_app.config["todo_repo"]["repo"]

    all_labels = gitlab.projects.get(personal_repo).labels.list(
        get_all=True
    )

    # Return dict of label name and label color
    return {label.name: label.color for label in all_labels}
