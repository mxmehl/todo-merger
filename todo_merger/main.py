"""Main"""

from flask import Blueprint, render_template

from ._issues import get_all_issues, prioritize_issues

main = Blueprint("main", __name__)


@main.route("/")
def index():
    """Index"""

    issues = get_all_issues()
    issues = prioritize_issues(issues)

    return render_template("index.html", issues=issues)
