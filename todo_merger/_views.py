"""View functions"""

import logging

from todo_merger._config import read_issues_config, write_issues_config
from todo_merger._issues import (
    ISSUE_RANKING_TABLE,
    IssueItem,
    IssuesStats,
    apply_user_issue_ranking,
    get_all_issues,
    get_issues_stats,
    prioritize_issues,
)


def view_issues() -> tuple[list[IssueItem], IssuesStats]:
    """Functions to view all issues"""
    config = read_issues_config()
    issues = get_all_issues()
    issues = prioritize_issues(issues)
    issues = apply_user_issue_ranking(issues=issues, ranking_dict=config)
    stats = get_issues_stats(issues)

    return issues, stats


def set_ranking(issue: str, rank: str) -> None:
    """Set new ranking of issue"""
    rank_int = ISSUE_RANKING_TABLE.get(rank, ISSUE_RANKING_TABLE["normal"])
    config = read_issues_config()

    if issue:
        # Check if new ranking is the same as old -> reset to default
        if issue in config and config.get(issue) == rank_int:
            logging.info("Resetting issue '%s' by removing it from issues configuration", issue)
            config.pop(issue)
        # Setting new ranking value
        else:
            logging.info("Setting rank of issue '%s' to %s (%s)", issue, rank, rank_int)
            config[issue] = rank_int

        # Update config file
        write_issues_config(issues_config=config)
