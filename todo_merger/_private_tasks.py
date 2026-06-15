"""Functions for dealing with a the private tasks repo."""

import logging
from typing import cast

from flask import current_app
from github import AuthenticatedUser, Github
from gitlab import Gitlab

from ._gitea import Gitea
from ._helpers import generate_instance_id


def private_tasks_repo_get_gitlab_labels(gitlab: Gitlab) -> dict[str, str]:
    """Get all labels from a GitLab repository."""
    private_tasks_repo = current_app.config["private_tasks_repo"]["repo"]

    all_labels = gitlab.projects.get(private_tasks_repo).labels.list(get_all=True)

    # Return dict of label name and label color
    return {label.name: label.color for label in all_labels}


def private_tasks_repo_get_github_labels(github: Github) -> dict[str, str]:
    """Get all labels from a GitHub repository."""
    private_tasks_repo = current_app.config["private_tasks_repo"]["repo"]

    all_labels = github.get_repo(private_tasks_repo).get_labels()

    # Return dict of label name and label color
    return {label.name: f"#{label.color}" for label in all_labels}


def private_tasks_repo_create_gitlab_issue(
    gitlab: Gitlab, title: str, labels: list[str]
) -> tuple[str, str]:
    """Create a new issue in the private tasks repository (GitLab). Returns
    (web_url, uid) of the new issue.
    """
    if gitlab.user is None:
        msg = "gitlab.user should be set after auth()"
        raise RuntimeError(msg)
    myuser_id = gitlab.user.id

    private_tasks_repo = current_app.config["private_tasks_repo"]["repo"]

    # Create issue
    result = gitlab.projects.get(private_tasks_repo).issues.create(
        {"title": title, "labels": labels, "assignee_id": myuser_id}
    )

    logging.debug("Created issue in repository '%s': %s", private_tasks_repo, result.web_url)

    instance_id = generate_instance_id(gitlab.url)
    uid = f"gitlab-{instance_id}-{result.id}"
    return result.web_url, uid


def private_tasks_repo_create_github_issue(
    github: Github, title: str, labels: list[str]
) -> tuple[str, str]:
    """Create a new issue in the private tasks repository (GitHub). Returns
    (web_url, uid) of the new issue.
    """
    private_tasks_repo = current_app.config["private_tasks_repo"]["repo"]
    myuser = cast("AuthenticatedUser.AuthenticatedUser", github.get_user())

    # Create issue
    result = github.get_repo(private_tasks_repo).create_issue(
        title=title, labels=labels, assignee=myuser.login
    )

    logging.debug("Created issue in repository '%s': %s", private_tasks_repo, result.html_url)

    uid = f"github-{result.id}"
    return result.html_url, uid


def private_tasks_repo_get_gitea_labels(gitea: Gitea) -> dict[str, str]:
    """Get all labels from a Gitea repository."""
    private_tasks_repo = current_app.config["private_tasks_repo"]["repo"]
    owner, repo = private_tasks_repo.split("/", 1)

    all_labels = gitea.get_repo_labels(owner, repo)

    # Return dict of label name and label color
    return {label["name"]: f"#{label['color']}" for label in all_labels}


def private_tasks_repo_create_gitea_issue(
    gitea: Gitea, title: str, labels: list[str]
) -> tuple[str, str]:
    """Create a new issue in the private tasks repository (Gitea). Returns
    (web_url, uid) of the new issue.
    """
    private_tasks_repo = current_app.config["private_tasks_repo"]["repo"]
    owner, repo = private_tasks_repo.split("/", 1)

    # Resolve label names to IDs
    all_labels = gitea.get_repo_labels(owner, repo)
    label_ids = [label["id"] for label in all_labels if label["name"] in labels]

    result = gitea.create_issue(
        owner, repo, title=title, labels=label_ids, assignee=str(gitea.user["login"])
    )

    logging.debug("Created issue in repository '%s': %s", private_tasks_repo, result["html_url"])

    instance_id = generate_instance_id(gitea.url)
    uid = f"gitea-{instance_id}-{result['id']}"
    return result["html_url"], uid
