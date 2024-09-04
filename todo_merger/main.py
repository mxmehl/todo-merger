"""Main"""

from flask import Blueprint, render_template

from ._issues import (
    apply_user_issue_ranking,
    get_all_issues,
    get_issues_stats,
    prioritize_issues,
)

main = Blueprint("main", __name__)


@main.route("/")
def index():
    """Index Page"""

    issues = get_all_issues()
    issues = prioritize_issues(issues)
    issues = apply_user_issue_ranking(
        issues=issues, ranking_dict={"gitlab-10f1c9-167043": 99, "github-2366029004": -1}
    )
    stats = get_issues_stats(issues)

    return render_template("index.html", issues=issues, stats=stats)
