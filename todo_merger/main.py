"""Main"""

from datetime import datetime

from flask import Blueprint, current_app, redirect, render_template, request

from ._cache import add_to_seen_issues, get_cache_status
from ._views import get_issues_and_stats, set_ranking

main = Blueprint("main", __name__)


@main.route("/", methods=["GET"])
def index():
    """Index Page"""

    # Find out whether current cache timer is still valid
    cache = get_cache_status(
        cache_timer=current_app.config["current_cache_timer"],
        timeout_seconds=current_app.config["cache_timeout_seconds"],
    )
    # Reset cache timer to now
    if not cache:
        current_app.config["current_cache_timer"] = datetime.now()

    issues, stats, new_issues = get_issues_and_stats(cache=cache)

    return render_template("index.html", issues=issues, stats=stats, new_issues=new_issues)


@main.route("/ranking", methods=["GET"])
def ranking():
    """Set ranking"""

    issue = request.args.get("issue", "")
    rank_new = request.args.get("rank", "")

    # Set ranking
    set_ranking(issue=issue, rank=rank_new)
    # When ranking an issue, it also makes the issue be marked as seen
    add_to_seen_issues(issues=[issue])

    return redirect("/")


@main.route("/reload", methods=["GET"])
def reload():
    """Reload all issues and break cache"""

    current_app.config["current_cache_timer"] = None

    return redirect("/")


@main.route("/mark-as-seen", methods=["GET"])
def mark_as_seen():
    """Mark one or all issues as seen"""

    issues = request.args.get("issues", "").split(",")

    add_to_seen_issues(issues=issues)

    return redirect("/")
