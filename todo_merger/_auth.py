"""Login functions."""

import logging
import sys

from github import Github
from gitlab import Gitlab

from ._config import default_config_file_path
from ._gitea import Gitea


def github_login(token: str) -> Github:
    """Login to GitHub with token."""
    if not token:
        logging.critical(
            "You need to provide a token for GitHub. Add that to your configuration file. "
            "Default: %s",
            default_config_file_path(),
        )
        sys.exit(1)
    g = Github(login_or_token=token)
    logging.info("Logged into GitHub as %s", g.get_user().login)
    return g


def gitlab_login(token: str, url: str = "https://gitlab.com") -> Gitlab:
    """Login to GitHub with token."""
    if not token:
        logging.critical(
            "You need to provide a token for GitLab. Add that to your configuration file. "
            "Default: %s",
            default_config_file_path(),
        )
        sys.exit(1)

    g = Gitlab(url=url, private_token=token)
    # Perform login, populates the user attribute
    g.auth()
    if g.user is None:
        msg = "g.user should be set after auth()"
        raise RuntimeError(msg)
    logging.info("Logged into GitLab as %s on %s", g.user.username, url)
    return g


def gitea_login(token: str, url: str) -> Gitea:
    """Login to Gitea with token."""
    if not token:
        logging.critical(
            "You need to provide a token for Gitea. Add that to your configuration file. "
            "Default: %s",
            default_config_file_path(),
        )
        sys.exit(1)
    return Gitea(url=url, token=token)
