"""Functions for dealing with a the private tasks repo"""

import logging

from flask import current_app
from github import AuthenticatedUser, Github
from gitlab import Gitlab


def private_tasks_repo_get_gitlab_labels(gitlab: Gitlab) -> dict[str, str]:
    """Get all labels from a GitLab repository"""
    private_tasks_repo = current_app.config["private_tasks_repo"]["repo"]

    all_labels = gitlab.projects.get(private_tasks_repo).labels.list(get_all=True)

    # Return dict of label name and label color
    return {label.name: label.color for label in all_labels}


def private_tasks_repo_get_github_labels(github: Github) -> dict[str, str]:
    """Get all labels from a GitHub repository"""
    private_tasks_repo = current_app.config["private_tasks_repo"]["repo"]

    all_labels = github.get_repo(private_tasks_repo).get_labels()

    # Return dict of label name and label color
    return {label.name: f"#{label.color}" for label in all_labels}


def private_tasks_repo_create_gitlab_issue(gitlab: Gitlab, title: str, labels: list[str]) -> str:
    """Create a new issue in the private tasks repository (GitLab). Returns the
    web URL of the new issue"""
    myuser_id = gitlab.user.id  # type: ignore

    private_tasks_repo = current_app.config["private_tasks_repo"]["repo"]

    # Create issue
    result = gitlab.projects.get(private_tasks_repo).issues.create(
        {"title": title, "labels": labels, "assignee_id": myuser_id}
    )

    logging.debug("Created issue in repository '%s': %s", private_tasks_repo, result.web_url)

    return result.web_url


def private_tasks_repo_create_github_issue(github: Github, title: str, labels: list[str]) -> str:
    """Create a new issue in the private tasks repository (GitHub). Returns the
    web URL of the new issue"""
    private_tasks_repo = current_app.config["private_tasks_repo"]["repo"]
    myuser: AuthenticatedUser.AuthenticatedUser = github.get_user()  # type: ignore

    # Create issue
    result = github.get_repo(private_tasks_repo).create_issue(
        title=title, labels=labels, assignee=myuser.login
    )

    logging.debug("Created issue in repository '%s': %s", private_tasks_repo, result.html_url)

    return result.html_url
