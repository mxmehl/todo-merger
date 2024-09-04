"""Main"""

from flask import Blueprint, redirect, render_template, request

from ._views import set_ranking, view_issues

main = Blueprint("main", __name__)


@main.route("/", methods=["GET"])
def index():
    """Index Page"""

    issues, stats = view_issues()

    return render_template("index.html", issues=issues, stats=stats)


@main.route("/ranking", methods=["GET"])
def ranking():
    """Set ranking"""

    issue = request.args.get("issue", "")
    rank_new = request.args.get("rank", "")

    set_ranking(issue=issue, rank=rank_new)

    return redirect("/")
