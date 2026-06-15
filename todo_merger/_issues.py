"""Handling issues which come in from different sources."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from flask import current_app

from ._types import IssueItem, IssuesStats

ISSUE_RANKING_TABLE = {"pin": -1, "high": 1, "normal": 5, "low": 99}


# ----------------------------------------
# ISSUES FETCHING FROM ALL SERVICES
# ----------------------------------------


def _fetch_service_issues(
    svc_type: str,
    login_obj: object,
    name: str,
) -> list[IssueItem]:
    """Dispatch to the correct fetch function for the given service type."""
    # Import here to avoid circular dependency
    from ._gitea import gitea_get_issues  # noqa: PLC0415
    from ._github import github_get_issues  # noqa: PLC0415
    from ._gitlab import gitlab_get_issues  # noqa: PLC0415
    from ._msplanner import msplannerfile_get_issues  # noqa: PLC0415

    if svc_type == "github":
        logging.info("Getting assigned GitHub issues for %s", name)
        return github_get_issues(login_obj)  # ty: ignore[invalid-argument-type]
    if svc_type == "gitlab":
        logging.info("Getting assigned GitLab issues for %s", name)
        return gitlab_get_issues(login_obj)  # ty: ignore[invalid-argument-type]
    if svc_type == "gitea":
        logging.info("Getting assigned Gitea issues for %s", name)
        return gitea_get_issues(login_obj)  # ty: ignore[invalid-argument-type]
    if svc_type == "msplanner-file":
        logging.info("Getting assigned MS Planner tasks for %s", name)
        return msplannerfile_get_issues(login_obj)  # ty: ignore[invalid-argument-type]
    logging.warning("Service %s not supported for fetching issues", svc_type)
    return []


def _fetch_one_service(
    svc_type: str,
    login_obj: object,
    name: str,
) -> tuple[str, list[IssueItem] | None, str | None]:
    """Fetch issues for a single service. Returns (name, issues_or_None, error_or_None).

    Designed to run inside a ThreadPoolExecutor — no Flask context needed.
    """
    try:
        svc_issues = _fetch_service_issues(svc_type, login_obj, name)
        for issue in svc_issues:
            issue.instance = name
    except Exception as exc:  # noqa: BLE001
        error_msg = f"{type(exc).__name__}: {exc}"
        logging.warning(
            "Failed to fetch issues for service '%s' (%s). Falling back to cached data. Error: %s",
            name,
            svc_type,
            error_msg,
            exc_info=True,
        )
        return name, None, error_msg
    else:
        return name, svc_issues, None


def get_all_issues() -> tuple[list[IssueItem], dict[str, str]]:
    """Get all issues from the supported services.

    Returns a tuple of (all_issues, degraded_services) where degraded_services
    maps service name to an error message for any instance that could not be
    reached. Stale cached data is used as a fallback for unreachable instances.

    Services are fetched in parallel using threads.
    """
    # Import here to avoid circular dependency
    from ._auth import try_service_login  # noqa: PLC0415
    from ._cache import read_instance_cache, write_instance_cache  # noqa: PLC0415

    issues: list[IssueItem] = []
    degraded: dict[str, str] = {}

    # Phase 1: re-login attempts and unreachable handling (main thread, mutates app config)
    fetchable: list[tuple[str, str, object]] = []  # (name, svc_type, login_obj)
    for name, service in current_app.config["services"].items():
        svc_type, login_obj, credentials = service[0], service[1], service[2]

        # Attempt re-login if the login object is missing (e.g. VPN was down at startup)
        if login_obj is None and svc_type != "msplanner-file":
            logging.info("Attempting re-login for service '%s'", name)
            login_obj = try_service_login(svc_type, credentials)
            if login_obj is not None:
                current_app.config["services"][name] = (svc_type, login_obj, credentials)

        # Still no login object after retry — treat as unreachable
        if login_obj is None:
            error_msg = "Service unreachable (no login object available)"
            logging.warning(
                "Skipping fetch for service '%s' — no login object. Falling back to cached data.",
                name,
            )
            degraded[name] = error_msg
            current_app.config["degraded_services"][name] = error_msg
            issues.extend(read_instance_cache(name))
            continue

        fetchable.append((name, svc_type, login_obj))

    # Phase 2: fetch all reachable services in parallel
    # max_workers capped at 8; upgrade to asyncio if service count grows much beyond that
    with ThreadPoolExecutor(max_workers=min(len(fetchable), 8) or 1) as pool:
        futures = {
            pool.submit(_fetch_one_service, svc_type, login_obj, name): name
            for name, svc_type, login_obj in fetchable
        }

        for future in as_completed(futures):
            name, svc_issues, error_msg = future.result()

            if svc_issues is not None:
                write_instance_cache(name, svc_issues)
                current_app.config["degraded_services"].pop(name, None)
                issues.extend(svc_issues)
            else:
                assert error_msg is not None  # noqa: S101
                degraded[name] = error_msg
                current_app.config["degraded_services"][name] = error_msg
                stale = read_instance_cache(name)
                logging.info("Using %d stale cached issue(s) for service '%s'", len(stale), name)
                issues.extend(stale)

    return issues, degraded


# ----------------------------------------
# ISSUE PRIORIZATION AND FILTERING
# ----------------------------------------


def apply_user_issue_config(
    issues: list[IssueItem], issue_config_dict: dict[str, dict[str, int | bool]]
) -> list[IssueItem]:
    """Apply local user configuration to issues."""
    for issue in issues:
        if issue.uid in issue_config_dict:
            issue.rank = issue_config_dict[issue.uid].get("rank", ISSUE_RANKING_TABLE["normal"])
            logging.debug("Applied rank %s to issue %s (%s)", issue.rank, issue.uid, issue.title)
            if issue_config_dict[issue.uid].get("todolist", False):
                logging.debug("Put issue %s on todo list (%s)", issue.uid, issue.title)
                issue.todolist = True

    return issues


def apply_issue_filter(issues: list[IssueItem], issue_filter: str | None) -> list[IssueItem]:
    """Apply issue filter to issues."""
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
    """Create some stats about the collected issues."""
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
