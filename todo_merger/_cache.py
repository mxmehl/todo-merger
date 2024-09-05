"""Cache functions"""

import json
import logging
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
