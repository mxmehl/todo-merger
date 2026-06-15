# ToDo Merger

Get a unified overview of all issues and tasks assigned to you across multiple platforms. A local web dashboard that aggregates GitHub, GitLab, Gitea, and Microsoft Planner into a single view, with personal prioritisation and a private task list. Additionally, a CLI for quick access to your tasks and labels.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
[![License: GPL-3.0-only](https://img.shields.io/badge/license-GPL--3.0--only-blue)](LICENSE.txt)
[![PyPI](https://img.shields.io/pypi/v/todo-merger)](https://pypi.org/project/todo-merger/)


## Features

- **Multi-platform aggregation** — pulls assigned issues, merge/pull requests, and tasks from GitHub, one or more GitLab instances, Gitea instances, and local Microsoft Planner exports, all into a single view
- **Graceful degradation** — if an instance is unreachable (e.g. a company GitLab behind a VPN), the app keeps running and shows cached data for that instance with a warning banner; other services are unaffected. Connectivity is retried automatically on the next cache refresh
- **Personal prioritisation** — pin, promote, or deprioritise any issue without touching the upstream tracker; rankings are stored locally
- **Todo list** — mark individual issues as personal todos and filter the view to show only those
- **New issue highlighting** — issues you haven't seen before are highlighted until you dismiss them
- **Private task creation** — create new issues directly in a configured private repository (GitHub, GitLab, or Gitea) from within the dashboard
- **Configurable display** — toggle which metadata columns are shown (labels, milestones, epics, assignees, due dates, refs, …)
- **Daemon mode** — run as a background process with `todo-merger web -d` / `todo-merger web stop`
- **CLI** — quickly list all open tasks as JSON, a compact table, or verbose human-readable output; create new issues and list available labels from the private tasks repo
- **Fast cache** — configurable cache timeout (default 10 minutes) avoids hammering the APIs on every page load; manual refresh available at any time


## Installation

### pipx (recommended)

[pipx](https://pypa.github.io/pipx/) installs the app in an isolated environment and keeps it off your system Python.

```sh
pip3 install pipx          # install pipx if not already present
pipx install todo-merger   # install todo-merger
```

todo-merger will be available in `~/.local/bin` (add to `$PATH` if needed).

To run without installing permanently:

```sh
pipx run todo-merger
```

To upgrade:

```sh
pipx upgrade todo-merger
```

### Other methods

```sh
pip install todo-merger   # plain pip
uv tool install todo-merger  # uv
```


## Usage

Please see `todo-merger --help` for the latest usage instructions.

```sh
todo-merger [global options] <command> [command options]
```

**Global options:**

| Flag | Description |
|------|-------------|
| `-c`, `--config-file` | Path to the config file (default: `~/.config/todo-merger/config.toml`) |
| `-v` | INFO logging |
| `-vv` | DEBUG logging |
| `-vvv` | DEBUG logging including verbose HTTP client logs |
| `--version` | Show version and exit |

**Commands:**

| Command | Description |
|---------|-------------|
| `web` | Start the web interface (open <http://localhost:8636>) |
| `web -d` | Start in daemon (background) mode |
| `web stop` | Stop a running background instance |
| `web --port PORT` | Use a custom port |
| `list` | List all open tasks as JSON |
| `list --table` | Compact table view (rank, title, clickable link) |
| `list --plain` | Verbose human-readable output |
| `list --cache` | Use cached data without fetching from APIs |
| `labels` | List available labels from the private tasks repo |
| `create TITLE` | Create a new issue in the private tasks repo |
| `create TITLE --rank pin` | Create and immediately rank the issue |
| `create TITLE --label bug` | Create with a label (repeatable) |


## Configuration

On first start, todo-merger creates an empty config file at `~/.config/todo-merger/config.toml`. Edit it to add your service credentials.

See [`DEFAULT_APP_CONFIG` in `_config.py`](todo_merger/_config.py) for all available options and their defaults.

Multiple instances of the same platform are supported — just add more `[services.*]` sections with unique names.

### Unavailable instances

If a service is currently unavailable (e.g. because company VPN is disconnected), todo-merger handles it gracefully:

- **App starts without connection** — the unreachable instance is skipped and recorded as degraded; a warning banner is shown in the dashboard. Cached data from the last successful fetch is displayed.
- **Connection reestablished later** — the next cache refresh (or manual reload) automatically retries the login and fetch for the degraded instance. If it succeeds, the warning disappears.
- **Connection drops mid-session** — the failing instance falls back to its last cached data; all other services continue normally.

No configuration is needed for this behaviour — it is automatic.


## License

The main license of this project is the GNU General Public License 3.0, no later version (`GPL-3.0-only`), Copyright Max Mehl.

Third-party components included under their respective licenses: Pico CSS (MIT), snippets from DB Systel (Apache-2.0).
