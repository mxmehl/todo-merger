"""Shared type definitions to avoid circular imports"""

from dataclasses import asdict, dataclass, field
from datetime import datetime

from ._helpers import convert_to_datetime, time_ago


@dataclass
class IssueItem:  # pylint: disable=too-many-instance-attributes
    """Dataclass holding a single issue"""

    assignee_users: list = field(default_factory=list)
    due_date: str = ""
    epic_title: str = ""
    labels: list = field(default_factory=list)
    milestone_title: str = ""
    pull: bool = False
    rank: int = 5  # Will be updated with ISSUE_RANKING_TABLE["normal"]
    ref: str = ""
    service: str = ""
    title: str = ""
    todolist: bool = False
    uid: str = ""
    updated_at_display: str = ""
    updated_at: datetime = field(default_factory=datetime.now)
    web_url: str = ""

    def import_values(self, **kwargs):
        """Import data from a dict"""
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    def fill_remaining_fields(self):
        """Fill remaining fields that have not been imported directly and which
        are solely derived from attribute values"""

        # updated_at_display
        self.updated_at_display = time_ago(convert_to_datetime(self.updated_at))

    def convert_to_dict(self):
        """Return the current dataclass as dict"""
        return asdict(self)


@dataclass
class IssuesStats:  # pylint: disable=too-many-instance-attributes
    """Dataclass holding a stats about all issues"""

    total: int = 0
    gitlab: int = 0
    github: int = 0
    msplanner: int = 0
    pulls: int = 0
    issues: int = 0
    due_dates_total: int = 0
    milestones_total: int = 0
    epics_total: int = 0
