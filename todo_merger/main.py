"""Main"""

from flask import Blueprint, render_template

from ._issues import get_all_issues, get_issues_stats, prioritize_issues

main = Blueprint("main", __name__)


@main.route("/")
def index():
    """Index Page"""

    issues = get_all_issues()
    issues = prioritize_issues(issues)
    stats = get_issues_stats(issues)

    return render_template("index.html", issues=issues, stats=stats)
