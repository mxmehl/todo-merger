"""Module to parse Microsoft Planner JSON export files."""

import json
import logging

from ._types import IssueItem


class MSPlannerFile:  # pylint: disable=too-few-public-methods
    """Class to parse Microsoft Planner JSON export files."""

    def __init__(self, file: str) -> None:

        try:
            with open(file, "r", encoding="UTF-8") as f:
                self.data = json.load(f)
        except FileNotFoundError as err:
            raise FileNotFoundError(f"Could not find MS Planner export file '{file}'") from err
        except json.JSONDecodeError as err:
            raise ValueError(f"Could not parse MS Planner export file '{file}'") from err


def _import_msplannerfile_issues(issues: list[dict]) -> list[IssueItem]:
    """Create a list of IssueItem from the MS Planner file"""
    issueitems: list[IssueItem] = []
    for issue in issues:
        if issue.get("completedDateTime", False):
            logging.debug("Skipping completed MS Planner task '%s'", issue.get("title", ""))
            continue
        d = IssueItem()
        d.import_values(
            assignee_users="",
            due_date=issue.get("dueDateTime", "")[:10],
            epic_title="",
            labels=[],
            milestone_title="",
            pull="",
            ref="",
            service="msplanner",
            title=issue.get("title", ""),
            uid=f"msplanner-{issue.get('id', '')}",
            updated_at=issue.get("createdDateTime", ""),
            web_url=(
                "https://planner.cloud.microsoft/webui/plan/"
                f"{issue.get('planId', '')}/view/board/task/{issue.get('id', '')}"
            ),
        )
        d.fill_remaining_fields()
        issueitems.append(d)

    return issueitems


def msplannerfile_get_issues(msplannerfile: MSPlannerFile) -> list[IssueItem]:
    """Get all issues assigned to authenticated user"""
    issues: list[IssueItem] = []

    issues.extend(_import_msplannerfile_issues(issues=msplannerfile.data))

    return issues
