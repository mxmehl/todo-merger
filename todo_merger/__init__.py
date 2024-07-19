"""App Init"""

import argparse
import logging
import sys
from importlib.metadata import version

import setuptools
from flask import Flask
from github import Github
from gitlab import Gitlab
from sassutils.wsgi import SassMiddleware

from ._auth import github_login, gitlab_login
from ._config import get_app_config

__version__ = version("todo-merger")

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument(
    "-c",
    "--config-file",
    help="Path to the app config file in a non-default location",
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)


logging.basicConfig(level=logging.DEBUG)


def load_app_config(config_file: str) -> dict[str, tuple[str, Github | Gitlab]]:
    """Load the app config, handle service logins, and return objects"""
    app_config: dict[str, dict[str, str]] = get_app_config(config_file)
    service_objects: dict[str, tuple[str, Github | Gitlab]] = {}

    for name, cfg in app_config.items():
        service = cfg.get("service", "")
        url = cfg.get("url", "")
        token = cfg.get("token", "")

        if not service:
            logging.critical(
                "The config section %s has no 'service' defined, e.g. 'github' or 'gitlab'", name
            )
            sys.exit(1)

        if service == "gitlab" and not url:
            logging.critical(
                "The config section %s is a gitlab service but has no 'url' defined", name
            )
            sys.exit(1)

        if name in service_objects:
            logging.critical(
                "You have used the section name %s more than once. Please make them unique", name
            )
            sys.exit(1)

        if service == "github":
            loginobj = github_login(token)
        elif service == "gitlab":
            loginobj = gitlab_login(token, url)  # type: ignore
        else:
            logging.critical("The config section %s contains an unknown 'service'", name)
            sys.exit(1)

        service_objects[name] = (service, loginobj)

    return service_objects


# pylint: disable=import-outside-toplevel
def create_app(config_file: str):
    """Create Flask App"""
    app = Flask(__name__)
    # Reload templates
    app.jinja_env.auto_reload = True
    app.jinja_env.lstrip_blocks = False
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    app.wsgi_app = SassMiddleware(  # type: ignore
        app.wsgi_app,
        {
            "todo_merger": {
                "sass_path": "static/sass",
                "css_path": "static/css",
                "wsgi_path": "/static/css",
                "strip_extension": False,
            }
        },
    )

    # Load app config and login to services (e.g. GitHub and GitLab)
    app.config["services"] = {}
    for name, service in load_app_config(config_file).items():
        app.config["services"][name] = service

    # blueprint for app
    from .main import main as main_blueprint  # pylint: disable=import-error

    app.register_blueprint(main_blueprint)

    return app


def main():
    """Main entry point for running the app."""
    args = parser.parse_args()
    app = create_app(config_file=args.config_file)
    app.run(port=8636)
