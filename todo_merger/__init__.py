"""ToDo Merger: Provide an overview of your assigned issues on GitLab and GitLab"""

import argparse
import logging
import signal
import sys
from importlib.metadata import version
from os import kill, path

from flask import Flask
from github import Github
from gitlab import Gitlab
from platformdirs import user_log_dir, user_runtime_dir
from sassutils.wsgi import SassMiddleware

try:
    import daemon
    import daemon.pidfile
# pwd does not exist on Windows, we cannot daemonize there
except (ModuleNotFoundError, ImportError):
    daemon = None

from ._auth import github_login, gitlab_login
from ._config import default_config_file_path, get_app_config

LOGFILE = path.join(user_log_dir("todo-merger", ensure_exists=True), "todo-merger.log")
PIDFILE = path.join(user_runtime_dir("todo-merger", ensure_exists=True), "todo-merger.pid")

__version__ = version("todo-merger")

parser = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
subparsers = parser.add_subparsers(dest="command", help="Special commands")

parser.add_argument(
    "-c", "--config-file", help="Path to the app config file ", default=default_config_file_path()
)
parser.add_argument(
    "-d",
    "--daemon",
    help="Start the app in the background and log to a file",
    action="store_true",
)
parser.add_argument(
    "-l", "--logfile", help="Path to the log file (in daemon mode)", default=LOGFILE
)
parser.add_argument(
    "-p", "--pidfile", help="Path to the PID file (in daemon mode)", default=PIDFILE
)
parser.add_argument(
    "-v",
    "--verbose",
    help="Activate INFO logging",
    action="store_true",
)
parser.add_argument(
    "-vv",
    "--debug",
    help="Activate DEBUG logging (even more than INFO)",
    action="store_true",
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)

# Special commands
parser_stop = subparsers.add_parser(
    "stop",
    help="Stop the running todo-merger background instance",
)


def configure_logger(args) -> logging.Logger:
    """Set logging options"""
    log = logging.getLogger()
    logging.basicConfig(
        encoding="utf-8",
        format="%(levelname)s in %(module)s: %(message)s",
        level=(logging.DEBUG if args.debug else logging.INFO if args.verbose else logging.WARNING),
        handlers=[logging.StreamHandler()],
    )

    return log


def load_app_services_config(
    config_file: str, section: str = "services"
) -> dict[str, tuple[str, Github | Gitlab]]:
    """Load the app config, handle service logins, and return objects"""
    app_config: dict[str, dict[str, str]] = get_app_config(config_file, section)
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

    # Initiate Flask app
    app = Flask(__name__)
    # Reload templates
    app.jinja_env.auto_reload = True
    app.jinja_env.lstrip_blocks = False
    app.jinja_env.globals["app_version"] = __version__
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    # Set werkzeug logging level to the global logging level
    logging.getLogger("werkzeug").setLevel(logging.root.level)

    # Settings for SCSS conversion
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
    for name, service in load_app_services_config(config_file).items():
        app.config["services"][name] = service

    # Initiate cache timer
    app.config["current_cache_timer"] = None
    app.config["cache_timeout_seconds"] = get_app_config(config_file, "cache").get(
        "timeout_seconds", 600
    )

    # blueprint for app
    from .main import main as main_blueprint  # pylint: disable=import-error

    app.register_blueprint(main_blueprint)

    return app


def run_server(config_file: str):
    """Run the Flask server"""
    app = create_app(config_file=config_file)
    app.run(port=8636)


def main():
    """Main entry point for running the app."""
    args = parser.parse_args()

    # Configure logger
    logger = configure_logger(args=args)

    # Stop app if requested
    if args.command == "stop":
        try:
            with open(args.pidfile, "r", encoding="utf-8") as pidreader:
                pid = int(pidreader.read())
                print(f"Sending SIGTERM to process {pid}")
                kill(pid, signal.SIGTERM)
                sys.exit()
        except FileNotFoundError:
            sys.exit(
                f"PID file {args.pidfile} does not seem to exist. The app does not seem to run "
                "normally or at all. Check your task manager and process list."
            )

    # Start app
    print("ToDo Merger will be available on http://localhost:8636")
    if args.daemon:
        if daemon is None:
            sys.exit(
                "Daemonizing this app is not possible on your system, e.g. because it's Windows."
            )
        with daemon.DaemonContext(pidfile=daemon.pidfile.TimeoutPIDLockFile(args.pidfile)):
            # Add file logger
            logger.addHandler(logging.FileHandler(args.logfile))

            # Run server
            run_server(config_file=args.config_file)
    else:
        run_server(config_file=args.config_file)
