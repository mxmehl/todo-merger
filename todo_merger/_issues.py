"""Handling issues which come in from different sources"""

import logging
from dataclasses import fields
from datetime import datetime

from flask import current_app

from ._types import IssueItem, IssuesStats

ISSUE_RANKING_TABLE = {"pin": -1, "high": 1, "normal": 5, "low": 99}


# ----------------------------------------
# ISSUES FETCHING FROM ALL SERVICES
# ----------------------------------------


def get_all_issues() -> list[IssueItem]:
    """Get all issues from the supported services"""
    # Import here to avoid circular dependency
    # pylint: disable=import-outside-toplevel
    from ._github import github_get_issues
    from ._gitlab import gitlab_get_issues
    from ._msplanner import msplannerfile_get_issues

    issues: list[IssueItem] = []
    for name, service in current_app.config["services"].items():
        if service[0] == "github":
            logging.info("Getting assigned GitHub issues for %s", name)
            issues.extend(github_get_issues(service[1]))
        elif service[0] == "gitlab":
            logging.info("Getting assigned GitLab issues for %s", name)
            issues.extend(gitlab_get_issues(service[1]))
        elif service[0] == "msplanner-file":
            logging.info("Getting assigned MS Planner tasks for %s", name)
            issues.extend(msplannerfile_get_issues(service[1]))
        else:
            print(f"Service {service[0]} not supported for fetching issues")

    return issues


# ----------------------------------------
# ISSUE PRIORIZATION AND FILTERING
# ----------------------------------------


def _replace_none_with_empty_string(obj: IssueItem) -> IssueItem:
    """Replace None values of a dataclass with an empty string. Makes sorting
    easier"""
    for f in fields(obj):
        value = getattr(obj, f.name)
        if value is None:
            setattr(obj, f.name, "")

    return obj


def prioritize_issues(
    issues: list[IssueItem], sort_by: list[tuple[str, bool]] | None = None
) -> list[IssueItem]:
    """
    Sorts the list of IssueItem objects based on multiple criteria.

    :param issues: List of IssueItem objects to sort.

    :param sort_by: List of tuples where each tuple contains:
                    - field name to sort by as a string
                    - a boolean indicating whether to sort in reverse order
                      (True for descending, False for ascending)

    :return: Sorted list of IssueItem objects.
    """
    if sort_by is None:
        sort_by = [
            ("due_date", False),
            ("milestone_title", True),
            ("epic_title", True),
            ("updated_at", True),
        ]

    logging.info("Sort issues based on %s", sort_by)

    # Replace None with empty string in all tasks
    issues = [_replace_none_with_empty_string(task) for task in issues]

    def sort_key(issue: IssueItem) -> tuple:
        # Create a tuple of the field values to sort by, considering the reverse order
        key: list[tuple[int, str | None]] = []
        for f, reverse in sort_by:
            value: str | datetime = getattr(issue, f)
            # Convert datetime to str
            if isinstance(value, datetime):
                value = value.strftime("%s")
            elif isinstance(value, str):
                value = value.lower()
            is_empty: bool = value == ""
            # Place empty values at the end
            if is_empty:
                key.append((1, None))  # `1` indicates an empty value
            else:
                if reverse:
                    value = "".join(chr(255 - ord(char)) for char in value)
                key.append((0, value))  # `0` indicates a non-empty value
        return tuple(key)

    return sorted(issues, key=sort_key)


def apply_user_issue_config(
    issues: list[IssueItem], issue_config_dict: dict[str, dict[str, int | bool]]
) -> list[IssueItem]:
    """Apply local user configuration to issues"""
    for issue in issues:
        if issue.uid in issue_config_dict:
            issue.rank = issue_config_dict[issue.uid].get("rank", ISSUE_RANKING_TABLE["normal"])
            logging.debug("Applied rank %s to issue %s (%s)", issue.rank, issue.uid, issue.title)
            if issue_config_dict[issue.uid].get("todolist", False):
                logging.debug("Put issue %s on todo list (%s)", issue.uid, issue.title)
                issue.todolist = True

    return issues


def apply_issue_filter(issues: list[IssueItem], issue_filter: str | None) -> list[IssueItem]:
    """Apply issue filter to issues"""
    if not issue_filter:
        logging.debug("No issue filter applied")

    logging.info("Applying issue filter '%s'", issue_filter)

    if issue_filter == "todolist":
        issues = [issue for issue in issues if issue.todolist]

    return issues


# ----------------------------------------
# STATS ABOUT FETCHED ISSUES
# ----------------------------------------


def get_issues_stats(issues: list[IssueItem]) -> IssuesStats:
    """Create some stats about the collected issues"""
    stats = IssuesStats()

    for issue in issues:
        # Total issues
        stats.total += 1
        # Services total
        setattr(stats, issue.service, getattr(stats, issue.service) + 1)
        # Issue/PR counter
        if issue.pull:
            stats.pulls += 1
        else:
            stats.issues += 1
        # Number of due dates, milestones, and epics
        stats.due_dates_total += 1 if issue.due_date else 0
        stats.milestones_total += 1 if issue.milestone_title else 0
        stats.epics_total += 1 if issue.epic_title else 0

    return stats
