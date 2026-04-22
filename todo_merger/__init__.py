"""ToDo Merger: Provide an overview of your assigned issues on GitHub, GitLab, and Gitea."""

import argparse
import logging
import signal
import sys
import types
import uuid
from importlib.metadata import version
from os import kill
from pathlib import Path
from typing import cast

from flask import Flask
from github import Github
from gitlab import Gitlab
from platformdirs import user_log_dir, user_runtime_dir
from sass_embedded import compile_directory
from sass_embedded.dart_sass.installer import install as install_dart_sass

from ._auth import try_service_login
from ._config import default_config_file_path, get_app_config
from ._gitea import Gitea
from ._msplanner import MSPlannerFile

daemon: types.ModuleType | None = None
try:
    import daemon
    import daemon.pidfile
# pwd does not exist on Windows, we cannot daemonize there
except (ModuleNotFoundError, ImportError):
    pass

LOGFILE = str(Path(user_log_dir("todo-merger", ensure_exists=True)) / "todo-merger.log")
PIDFILE = str(Path(user_runtime_dir("todo-merger", ensure_exists=True)) / "todo-merger.pid")

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
parser.add_argument("--port", help="Port the application runs on", type=int, default=8636)
parser.add_argument(
    "-v",
    "--verbose",
    help="Activate INFO logging",
    action="store_true",
)
parser.add_argument(
    "-vv",
    "--debug",
    help="Activate DEBUG logging",
    action="store_true",
)
parser.add_argument(
    "-vvv",
    "--debug-all",
    help="Activate DEBUG logging including verbose HTTP client logs (httpx etc.)",
    action="store_true",
)
parser.add_argument("--version", action="version", version="%(prog)s " + __version__)

# Special commands
parser_stop = subparsers.add_parser(
    "stop",
    help="Stop the running todo-merger background instance",
)


def configure_logger(args: argparse.Namespace) -> logging.Logger:
    """Set logging options."""
    log = logging.getLogger()
    logging.basicConfig(
        format="%(levelname)s in %(module)s: %(message)s",
        level=(
            logging.DEBUG
            if args.debug or args.debug_all
            else logging.INFO
            if args.verbose
            else logging.WARNING
        ),
        handlers=[logging.StreamHandler()],
    )

    # httpx is very chatty at DEBUG level; cap it at INFO unless -vvv is given
    if (args.debug or args.debug_all) and not args.debug_all:
        for noisy in ("httpx", "httpcore"):
            logging.getLogger(noisy).setLevel(logging.INFO)

    return log


def load_app_services_config(
    config_file: str, section: str = "services"
) -> dict[str, tuple[str, Github | Gitlab | Gitea | MSPlannerFile | None, dict[str, str]]]:
    """Load the app config, handle service logins, and return objects."""
    app_config: dict[str, dict[str, str]] = get_app_config(config_file, section)
    service_objects: dict[
        str, tuple[str, Github | Gitlab | Gitea | MSPlannerFile | None, dict[str, str]]
    ] = {}

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

        if service == "gitea" and not url:
            logging.critical(
                "The config section %s is a gitea service but has no 'url' defined", name
            )
            sys.exit(1)

        if name in service_objects:
            logging.critical(
                "You have used the section name %s more than once. Please make them unique", name
            )
            sys.exit(1)

        # Store credentials for later re-login attempts (e.g. after VPN reconnect)
        credentials: dict[str, str] = {"token": token, "url": url, "file": cfg.get("file", "")}

        # msplanner-file has no network login. All other services use try_service_login(),
        # which calls the individual login functions — those already call sys.exit(1) on a
        # missing token, so no duplicate checks are needed here.
        loginobj: Github | Gitlab | Gitea | MSPlannerFile | None
        if service in {"github", "gitlab", "gitea"}:
            loginobj = try_service_login(service, credentials)
        elif service == "msplanner-file":
            loginobj = MSPlannerFile(cfg.get("file", ""))
        else:
            logging.critical("The config section %s contains an unknown 'service'", name)
            sys.exit(1)

        service_objects[name] = (service, loginobj, credentials)

    return service_objects


def create_app(config_file: str) -> Flask:
    """Create Flask App."""
    # Initiate Flask app
    app = Flask(__name__)
    # Reload templates
    app.jinja_env.auto_reload = True
    app.jinja_env.lstrip_blocks = False
    cast("dict", app.jinja_env.globals).update({"app_version": __version__})
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    # Set werkzeug logging level to the global logging level
    logging.getLogger("werkzeug").setLevel(logging.root.level)

    # Configure and compile Sass to CSS
    install_dart_sass()  # downloads dart to venv
    projroot = Path(__file__).parent.resolve()
    compile_directory(projroot / Path("static/sass"), dest=projroot / Path("static/css"))

    # Set a secret key for the session
    app.secret_key = str(uuid.uuid4().hex)

    # Load app config and login to services (e.g. GitHub, GitLab, Gitea)
    app.config["services"] = {}
    for name, service in load_app_services_config(config_file).items():
        app.config["services"][name] = service

    # Track which services are currently unreachable (e.g. VPN-gated instances)
    app.config["degraded_services"]: dict[str, str] = {}
    for name, service in app.config["services"].items():
        if service[1] is None:
            app.config["degraded_services"][name] = "Could not connect during startup"

    # Initiate cache timer
    app.config["current_cache_timer"] = None
    app.config["cache_timeout_seconds"] = get_app_config(config_file, "cache").get(
        "timeout_seconds", 600
    )

    # Load display config and set default values
    app.config["display"] = get_app_config(config_file, "display")
    for display_cfg in (
        "show_assignees",
        "show_due_date",
        "show_epic",
        "show_labels",
        "show_milestone",
        "show_ref",
        "show_service",
        "show_type",
        "show_updated_at",
        "show_web_url",
    ):
        app.config["display"][display_cfg] = app.config["display"].get(display_cfg, True)

    # Get private-tasks-repo config
    if private_tasks_repo_config := get_app_config(
        config_file, "private-tasks-repo", warn_on_missing_key=False
    ):
        app.config["private_tasks_repo"] = private_tasks_repo_config
        # Find the GitHub/GitLab/Gitea service object that is configured for the private tasks repo
        try:
            _svc_type, _login, _creds = app.config["services"][
                app.config["private_tasks_repo"]["service"]
            ]
            app.config["private_tasks_repo"]["service"] = _svc_type
            app.config["private_tasks_repo"]["login"] = _login
        except KeyError:
            logging.critical(
                "The 'private-tasks-repo' section in the config file refers to "
                "a service that is not defined"
            )
            sys.exit(1)
    else:
        logging.info(
            "No 'private-tasks-repo' section found in config file. Disabling this functionality"
        )
        app.config["private_tasks_repo"] = None

    # Print app config in DEBUG
    logging.debug("App config: %s", app.config)

    # blueprint for app
    from .main import main as main_blueprint  # noqa: PLC0415

    app.register_blueprint(main_blueprint)

    return app


def run_server(config_file: str, port: int) -> None:
    """Run the Flask server."""
    app = create_app(config_file=config_file)
    app.run(port=port)


def main() -> None:
    """Main entry point for running the app."""
    args = parser.parse_args()

    # Configure logger
    logger = configure_logger(args=args)

    # Stop app if requested
    if args.command == "stop":
        try:
            with open(args.pidfile, encoding="utf-8") as pidreader:
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
    print(f"ToDo Merger will be available on http://localhost:{args.port}")
    logging.info("Config file: %s", args.config_file)
    logging.info("Log file: %s", args.logfile)
    logging.info("PID file: %s", args.pidfile)
    if args.daemon:
        if daemon is None:
            sys.exit(
                "Daemonizing this app is not possible on your system, e.g. because it's Windows."
            )
        with daemon.DaemonContext(pidfile=daemon.pidfile.TimeoutPIDLockFile(args.pidfile)):
            # Add file logger
            logger.addHandler(logging.FileHandler(args.logfile))

            # Run server
            run_server(config_file=args.config_file, port=args.port)
    else:
        run_server(config_file=args.config_file, port=args.port)
