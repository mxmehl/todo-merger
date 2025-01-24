"""Main"""

from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request
from werkzeug.wrappers import Response

from ._cache import add_to_seen_issues, get_cache_status
from ._views import (
    get_issues_and_stats,
    private_tasks_repo_create_issue,
    private_tasks_repo_get_labels,
    refresh_issues_cache,
    set_ranking,
    set_todolist,
)

main = Blueprint("main", __name__)


@main.route("/", methods=["GET"])
def index() -> str:
    """Index Page"""

    issue_filter = request.args.get("filter", None)

    # Find out whether current cache timer is still valid
    cache = get_cache_status(
        cache_timer=current_app.config["current_cache_timer"],
        timeout_seconds=current_app.config["cache_timeout_seconds"],
    )
    # Reset cache timer to now
    if not cache:
        current_app.config["current_cache_timer"] = datetime.now()

    try:
        issues, stats, new_issues = get_issues_and_stats(cache=cache, issue_filter=issue_filter)
    except Exception as ex:  # pylint: disable=broad-except
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        flash(message, "error")
        return render_template("error.html")

    # Find out if private tasks repo is configured
    private_private_tasks_repo_configured = current_app.config.get("private_tasks_repo", None)

    return render_template(
        "index.html",
        issues=issues,
        stats=stats,
        new_issues=new_issues,
        private_private_tasks_repo_configured=private_private_tasks_repo_configured,
        display_cfg=current_app.config["display"],
        issue_filter=issue_filter,
    )


@main.route("/ranking", methods=["GET"])
def ranking() -> Response:
    """Set ranking"""

    issue = request.args.get("issue", "")
    rank_new = request.args.get("rank", "")

    # Set ranking
    set_ranking(issue=issue, rank=rank_new)
    # When ranking an issue, it also makes the issue be marked as seen
    add_to_seen_issues(new_unseen_issues=[issue])

    return redirect(request.referrer)


@main.route("/todolist", methods=["GET"])
def todolist() -> Response:
    """Add or remove issue from todolist"""

    issue = request.args.get("issue", "")
    state = request.args.get("state", "")

    # Set ranking
    set_todolist(issue=issue, state=state)
    # When ranking an issue, it also makes the issue be marked as seen
    add_to_seen_issues(new_unseen_issues=[issue])

    return redirect(request.referrer)


@main.route("/reload", methods=["GET"])
def reload() -> Response:
    """Reload all issues and break cache"""

    refresh_issues_cache()

    return redirect("/")


@main.route("/mark-as-seen", methods=["GET"])
def mark_as_seen() -> Response:
    """Mark one or all issues as seen"""

    issues = request.args.get("issues", "").split(",")

    add_to_seen_issues(new_unseen_issues=issues)

    return redirect("/")


@main.route("/new", methods=["GET"])
def new_form() -> str:
    """Page form to create new issues"""

    labels = private_tasks_repo_get_labels()

    return render_template(
        "new.html",
        labels=labels,
        colored_labels=current_app.config["private_tasks_repo"]["colored_labels"],
    )


@main.route("/new", methods=["POST"])
def new_create() -> Response:
    """Create a new issue"""

    # Upon cancel request, also refresh cache
    if request.form.get("cancel"):
        refresh_issues_cache()
        return redirect("/")

    # Get relevant form data
    title: str = request.form.get("issue_title", "")
    labels: list[str] = request.form.getlist("labels")

    # Catch potential empty title
    if not title:
        flash("Issue title cannot be empty", "error")
        return redirect("/new")

    # Create new issue
    new_url = private_tasks_repo_create_issue(title=title, labels=labels)
    flash(f"New issue created: <a href='{new_url}' target='_blank'>{new_url}</a>", "success")

    # If user wants back to overview, refresh cache before to also get the newly created issue
    if request.form.get("submit_and_index"):
        refresh_issues_cache()
        return redirect("/")

    return redirect("/new")
