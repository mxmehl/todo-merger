"""Main"""

import logging

from flask import Blueprint, redirect, render_template, request

from ._config import read_issues_config, write_issues_config
from ._issues import (
    ISSUE_RANKING_TABLE,
    IssueItem,
    IssuesStats,
    apply_user_issue_ranking,
    get_all_issues,
    get_issues_stats,
    prioritize_issues,
)

main = Blueprint("main", __name__)


def view_issues() -> tuple[list[IssueItem], IssuesStats]:
    """Functions to view all issues"""
    config = read_issues_config()
    issues = get_all_issues()
    issues = prioritize_issues(issues)
    issues = apply_user_issue_ranking(issues=issues, ranking_dict=config)
    stats = get_issues_stats(issues)

    return issues, stats


@main.route("/", methods=["GET"])
def index():
    """Index Page"""

    issues, stats = view_issues()

    return render_template("index.html", issues=issues, stats=stats)


@main.route("/ranking", methods=["GET"])
def ranking():
    """Set ranking"""

    ranking_table = {"pin": -1, "high": 1, "low": 99}

    issue = request.args.get("issue")
    rank_new = request.args.get("rank", "")
    rank_new_int = ranking_table.get(rank_new, ISSUE_RANKING_TABLE["normal"])
    config = read_issues_config()

    if issue:
        # Check if new ranking is the same as old -> reset to default
        if issue in config and config.get(issue) == rank_new_int:
            logging.info("Resetting issue '%s' by removing it from issues configuration", issue)
            config.pop(issue)
        # Setting new ranking value
        else:
            logging.info("Setting rank of issue '%s' to %s (%s)", issue, rank_new, rank_new_int)
            config[issue] = rank_new_int

        # Update config file
        write_issues_config(issues_config=config)

    return redirect("/")
