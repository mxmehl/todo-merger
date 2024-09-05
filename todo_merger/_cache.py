"""Cache functions"""

import json
import logging
from datetime import datetime, timedelta
from os.path import join

from platformdirs import user_cache_dir

from ._issues import IssueItem


def read_issues_cache():
    """Return the issues cache"""
    cache_file = join(user_cache_dir("todo-merger", ensure_exists=True), "issues.json")

    logging.debug("Reading issues cache file %s", cache_file)
    try:
        with open(cache_file, mode="r", encoding="UTF-8") as jsonfile:
            list_of_dicts = json.load(jsonfile)

            # Convert to list of IssueItem
            list_of_dataclasses = []
            for element in list_of_dicts:
                list_of_dataclasses.append(IssueItem(**element))

            return list_of_dataclasses

    except json.decoder.JSONDecodeError:
        logging.error(
            "Cannot read JSON file %s. Please check its syntax or delete it. "
            "Will ignore any issues cache.",
            cache_file,
        )
        return {}

    except FileNotFoundError:
        logging.debug(
            "Issues cache file '%s' has not been found. Initializing a new empty one.",
            cache_file,
        )
        default_issues_cache: dict = {}
        write_issues_cache(issues=default_issues_cache)

        return default_issues_cache


def write_issues_cache(issues: list[IssueItem]) -> None:
    """Write issues cache file"""

    cache_file = join(user_cache_dir("todo-merger", ensure_exists=True), "issues.json")

    issues_cache = [issue.convert_to_dict() for issue in issues]

    logging.debug("Writing issues cache file %s", cache_file)
    with open(cache_file, mode="w", encoding="UTF-8") as jsonfile:
        json.dump(issues_cache, jsonfile, indent=2, default=str)


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
