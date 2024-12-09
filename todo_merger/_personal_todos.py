"""Functions for dealing with a the personal ToDo repo"""

import logging

from flask import current_app
from github import AuthenticatedUser, Github
from gitlab import Gitlab


def todo_repo_get_gitlab_labels(gitlab: Gitlab) -> dict[str, str]:
    """Get all labels from a GitLab repository"""
    personal_repo = current_app.config["todo_repo"]["repo"]

    all_labels = gitlab.projects.get(personal_repo).labels.list(get_all=True)

    # Return dict of label name and label color
    return {label.name: label.color for label in all_labels}


def todo_repo_get_github_labels(github: Github) -> dict[str, str]:
    """Get all labels from a GitHub repository"""
    personal_repo = current_app.config["todo_repo"]["repo"]

    all_labels = github.get_repo(personal_repo).get_labels()

    # Return dict of label name and label color
    return {label.name: f"#{label.color}" for label in all_labels}


def todo_repo_create_gitlab_issue(gitlab: Gitlab, title: str, labels: list[str]) -> str:
    """Create a new issue in the personal todo repository (GitLab). Returns the
    web URL of the new issue"""
    myuser_id = gitlab.user.id  # type: ignore

    personal_repo = current_app.config["todo_repo"]["repo"]

    # Create issue
    result = gitlab.projects.get(personal_repo).issues.create(
        {"title": title, "labels": labels, "assignee_id": myuser_id}
    )

    logging.debug("Created issue in repository '%s': %s", personal_repo, result.web_url)

    return result.web_url


def todo_repo_create_github_issue(github: Github, title: str, labels: list[str]) -> str:
    """Create a new issue in the personal todo repository (GitHub). Returns the
    web URL of the new issue"""
    personal_repo = current_app.config["todo_repo"]["repo"]
    myuser: AuthenticatedUser.AuthenticatedUser = github.get_user()  # type: ignore

    # Create issue
    result = github.get_repo(personal_repo).create_issue(
        title=title, labels=labels, assignee=myuser.login
    )

    logging.debug("Created issue in repository '%s': %s", personal_repo, result.html_url)

    return result.html_url
