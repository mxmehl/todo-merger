"""Cache functions"""

import json
import logging
from datetime import datetime, timedelta, timezone
from os.path import join

from platformdirs import user_cache_dir

from ._issues import IssueItem


def _read_cache_file(
    filename: str, instance: str = "list"
) -> list[dict] | dict[str, dict[str, int]]:
    """
    Return a JSON file from the cache directory.

    Args:
        filename (str): The name of the cache file to read.

        instance (str): The type of the expected return value. If "dict", an
        empty dictionary is returned in case of errors. Otherwise, an empty list
        is returned.

    Returns:
        list | dict: The content of the JSON file as a list of dictionaries or a
        dictionary of dictionaries with integer values. Returns an empty list or
        dictionary if the file is not found or cannot be read.
    """
    cache_file = join(user_cache_dir("todo-merger", ensure_exists=True), filename)

    empty_return: list | dict = {} if instance == "dict" else []

    logging.debug("Reading cache file %s", cache_file)
    try:
        with open(cache_file, mode="r", encoding="UTF-8") as jsonfile:
            return json.load(jsonfile)

    except json.decoder.JSONDecodeError:
        logging.error(
            "Cannot read JSON file %s. Please check its syntax or delete it. "
            "Will ignore any cache.",
            cache_file,
        )
        return empty_return

    except FileNotFoundError:
        logging.debug(
            "Cache file '%s' has not been found. Initializing a new empty one.",
            cache_file,
        )
        return empty_return


def _write_cache_file(filename: str, content: dict | list) -> None:
    """Write a JSON file to the cache directry"""
    cache_file = join(user_cache_dir("todo-merger", ensure_exists=True), filename)

    logging.debug("Writing cache file %s", cache_file)
    with open(cache_file, mode="w", encoding="UTF-8") as jsonfile:
        json.dump(content, jsonfile, indent=2, default=str)


def read_issues_cache() -> list[IssueItem]:
    """Return the current issue cache, or initialize empty one if none present"""
    issues_cache: list[dict] = _read_cache_file(filename="issues.json")  # type: ignore

    if issues_cache:
        # Convert to list of IssueItem
        list_of_dataclasses = []
        for element in issues_cache:
            list_of_dataclasses.append(IssueItem(**element))
        return list_of_dataclasses

    # Initialize empty issues cache
    write_issues_cache(issues=[])
    return []


def write_issues_cache(issues: list[IssueItem]) -> None:
    """Write issues cache file"""
    issues_as_dict = [issue.convert_to_dict() for issue in issues]

    _write_cache_file(filename="issues.json", content=issues_as_dict)


def get_cache_status(cache_timer: None | datetime, timeout_seconds: int) -> bool:
    """Find out whether the cache is still valid. Returns False if it must be
    refreshed"""

    if cache_timer is None:
        logging.debug("No cache timer set before, or manually refreshed")
        return False

    # Get difference between now and start of cache timer
    cache_diff = datetime.now() - cache_timer
    logging.debug("Current cache time difference: %s", cache_diff)
    if cache_diff > timedelta(seconds=timeout_seconds):
        logging.info("Cache older than defined. Requesting all issues anew")
        # Mark that cache shall be disregarded
        return False

    logging.debug("Cache is still considered to be valid")
    return True


def get_unseen_issues(issues: list[IssueItem]) -> dict[str, str]:
    """Return a list of issue IDs that haven't been seen before"""
    # Read seen file
    seen_issues_cached: dict[str, dict[str, int]] = _read_cache_file(
        filename="seen-issues.json", instance="dict"
    )  # type: ignore

    unseen_issues = {}

    for issue in issues:
        if issue.uid not in seen_issues_cached:
            logging.debug("Issue %s hasn't been seen before", issue.uid)
            unseen_issues[issue.uid] = issue.title

    return unseen_issues


def add_to_seen_issues(new_unseen_issues: list[str]) -> None:
    """Add one or multiple issues to the seen issues list"""

    # Read seen file
    seen_issues_cached: dict[str, dict[str, int]] = _read_cache_file(
        filename="seen-issues.json", instance="dict"
    )  # type: ignore

    # Extend seen issues with new list
    for new_issue in new_unseen_issues:
        logging.debug("Marking issue %s as seen", new_issue)
        seen_issues_cached[new_issue] = {"first_seen": int(datetime.now(timezone.utc).timestamp())}

    # Update file
    _write_cache_file(filename="seen-issues.json", content=seen_issues_cached)


def update_last_seen() -> None:
    """Update the last_seen flag of an issue in the cache"""
    issues_cache: list[dict] = _read_cache_file(filename="issues.json")  # type: ignore
    seen_issues_cached: dict[str, dict[str, int]] = _read_cache_file(
        filename="seen-issues.json", instance="dict"
    )  # type: ignore

    logging.debug("Updating last_seen flag for all %s issues in cache", len(issues_cache))
    for issue in issues_cache:
        uid = issue.get("uid", "")
        if uid in seen_issues_cached:
            seen_issues_cached[uid]["last_seen"] = int(datetime.now(timezone.utc).timestamp())
        else:
            logging.debug("Issue %s not found in seen issues cache", uid)

    _write_cache_file(filename="seen-issues.json", content=seen_issues_cached)
