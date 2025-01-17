"""App config file handling"""

import json
import logging
import sys
from os import makedirs
from os.path import dirname, join

import toml
from platformdirs import user_config_dir

DEFAULT_APP_CONFIG = """# App configuration for ToDo Merger

[cache]
timeout_seconds = 600

[services.github-com]
service = "github"
token = ""

[services.gitlab-com]
service = "gitlab"
token = ""
url = "https://gitlab.com"

# Private tasks repository configuration
# [private-tasks-repo]
# service = "github-com"
# repo = "my-username/todos"
# colored_labels = true

[display]
show_assignees = true
show_due_date = true
show_epic = true
show_labels = true
show_milestone = true
show_ref = true
show_service = true
show_type = true
show_updated_at = true
show_web_url = true
"""


def _initialize_config_file(configfile: str) -> dict:
    """Create a new app configuration file with default values"""

    # Create directory in case it does not exist
    makedirs(dirname(configfile), exist_ok=True)

    # Write the default config in TOML format to a new file
    with open(configfile, mode="w", encoding="UTF-8") as tomlfile:
        tomlfile.write(DEFAULT_APP_CONFIG)

    return toml.loads(DEFAULT_APP_CONFIG)


def _read_app_config_file(config_file: str) -> dict:
    """Read full app configuration"""
    try:
        with open(config_file, mode="r", encoding="UTF-8") as tomlfile:
            app_config = toml.load(tomlfile)

    except FileNotFoundError:
        logging.warning(
            "App configuration file '%s' has not been found. Initializing a new empty one.",
            config_file,
        )
        app_config = _initialize_config_file(config_file)

    except toml.decoder.TomlDecodeError:
        logging.error("Error reading configuration file '%s'. Check the syntax!", config_file)
        sys.exit(1)

    return app_config


def default_config_file_path() -> str:
    """Define the path of the config file"""
    return join(user_config_dir("todo-merger", ensure_exists=True), "config.toml")


def get_app_config(config_file: str, key: str = "", warn_on_missing_key: bool = True) -> dict:
    """Return a specific section from the app configuration, or the whole config"""

    if not config_file:
        config_file = default_config_file_path()

    if key:
        try:
            return _read_app_config_file(config_file)[key]
        except KeyError as e:
            if warn_on_missing_key:
                logging.warning("Key %s not found in configuration: %s", key, e)
            return {}

    return _read_app_config_file(config_file)


def read_issues_config() -> dict:
    """Return the issues configuration"""

    config_file = join(user_config_dir("todo-merger", ensure_exists=True), "issues-config.json")

    logging.debug("Reading issues configuration file %s", config_file)
    try:
        with open(config_file, mode="r", encoding="UTF-8") as jsonfile:
            return json.load(jsonfile)

    except json.decoder.JSONDecodeError:
        logging.error(
            "Cannot read JSON file %s. Please check its syntax or delete it. "
            "Will ignore any issues configuration.",
            config_file,
        )
        return {}

    except FileNotFoundError:
        logging.debug(
            "Issues configuration file '%s' has not been found. Initializing a new empty one.",
            config_file,
        )
        default_issues_config: dict = {}
        write_issues_config(issues_config=default_issues_config)

        return default_issues_config


def write_issues_config(issues_config: dict) -> None:
    """Write issues configuration file"""

    config_file = join(user_config_dir("todo-merger", ensure_exists=True), "issues-config.json")

    logging.debug("Writing issues configuration file %s", config_file)
    with open(config_file, mode="w", encoding="UTF-8") as jsonfile:
        json.dump(issues_config, jsonfile)
