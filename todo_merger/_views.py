"""View functions, removing complexity from main.py"""

import logging

from flask import current_app

from ._cache import (
    get_unseen_issues,
    read_issues_cache,
    update_last_seen,
    write_issues_cache,
)
from ._config import read_issues_config, write_issues_config
from ._issues import (
    ISSUE_RANKING_TABLE,
    IssueItem,
    IssuesStats,
    apply_issue_filter,
    apply_user_issue_config,
    get_all_issues,
    get_issues_stats,
    prioritize_issues,
)
from ._private_tasks import (
    private_tasks_repo_create_github_issue,
    private_tasks_repo_create_gitlab_issue,
    private_tasks_repo_get_github_labels,
    private_tasks_repo_get_gitlab_labels,
)


def get_issues_and_stats(
    cache: bool, issue_filter: str | None
) -> tuple[list[IssueItem], IssuesStats, dict[str, str]]:
    """Functions to view all issues. Returns: list of IssueItem, a IssueStats
    object, and list of issue IDs"""
    # Get issues (either cache or online)
    if cache:
        issues = read_issues_cache()
    else:
        # Get all issues from the services
        issues = get_all_issues()
        # Update cache file
        write_issues_cache(issues=issues)
        # Update last_seen flag in seen issues cache
        update_last_seen()
    # Get previously unseen issues
    new_issues = get_unseen_issues(issues=issues)
    # Default prioritization
    issues = prioritize_issues(issues)
    # Issues custom config (ranking)
    config = read_issues_config()
    issues = apply_user_issue_config(issues=issues, issue_config_dict=config)
    # Apply issue filter
    issues = apply_issue_filter(issues=issues, issue_filter=issue_filter)
    # Stats
    stats = get_issues_stats(issues)

    return issues, stats, new_issues


def set_ranking(issue: str, rank: str) -> None:
    """Set new ranking of individual issue inside of the issues configuration file"""
    rank_int = ISSUE_RANKING_TABLE.get(rank, ISSUE_RANKING_TABLE["normal"])
    config: dict[str, dict[str, int | bool]] = read_issues_config()

    # Catch undefined issues
    if not issue:
        return

    # Create new issue entry if it does not exist
    if issue not in config:
        config[issue] = {}

    # Check if new ranking is the same as old -> reset to default
    if issue in config and config.get(issue, {}).get("rank") == rank_int:
        logging.info("Resetting ranking for issue '%s'", issue)
        config[issue].pop("rank", None)
    # Setting new ranking value
    else:
        logging.info("Setting rank of issue '%s' to %s (%s)", issue, rank, rank_int)
        config[issue]["rank"] = rank_int

    # Update config file
    write_issues_config(issues_config=config)


def set_todolist(issue: str, state: str | bool) -> None:
    """Add or remove an issue from the personal todo list"""
    config = read_issues_config()

    # Convert state to bool if str
    if isinstance(state, str):
        state = state.lower() in ("yes", "true", "t", "1")

    # Catch undefined issues
    if not issue:
        return

    # Create new issue entry if it does not exist
    if issue not in config:
        config[issue] = {}

    if state:
        logging.info("Adding issue '%s' to the todo list", issue)
    else:
        logging.info("Removing issue '%s' from the todo list", issue)
    config[issue]["todolist"] = state

    # Update config file
    write_issues_config(issues_config=config)


def refresh_issues_cache() -> None:
    """Refresh the cache of issues"""
    current_app.config["current_cache_timer"] = None


def private_tasks_repo_get_labels() -> dict[str, str]:
    """Get all labels from the private tasks repository"""
    service, login = (
        current_app.config["private_tasks_repo"]["service"],
        current_app.config["private_tasks_repo"]["login"],
    )

    if service == "gitlab":
        return private_tasks_repo_get_gitlab_labels(gitlab=login)

    return private_tasks_repo_get_github_labels(github=login)


def private_tasks_repo_create_issue(title: str, labels: list[str]) -> str:
    """Create a new issue in the private tasks repository. Returns the web URL
    of the new issue"""
    service, login = (
        current_app.config["private_tasks_repo"]["service"],
        current_app.config["private_tasks_repo"]["login"],
    )

    if service == "gitlab":
        return private_tasks_repo_create_gitlab_issue(gitlab=login, title=title, labels=labels)

    return private_tasks_repo_create_github_issue(github=login, title=title, labels=labels)
