"""Module to parse Microsoft Planner JSON export files."""

import json


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
