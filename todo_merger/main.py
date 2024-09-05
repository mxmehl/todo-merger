"""Main"""

from datetime import datetime

from flask import Blueprint, current_app, redirect, render_template, request

from ._cache import get_cache_status
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

    issues, stats = get_issues_and_stats(cache=cache)

    return render_template("index.html", issues=issues, stats=stats)


@main.route("/ranking", methods=["GET"])
def ranking():
    """Set ranking"""

    issue = request.args.get("issue", "")
    rank_new = request.args.get("rank", "")

    set_ranking(issue=issue, rank=rank_new)

    return redirect("/")


@main.route("/reload", methods=["GET"])
def reload():
    """Reload all issues and break cache"""

    current_app.config["current_cache_timer"] = None

    return redirect("/")
