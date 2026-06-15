# Agent Guidelines for todo-merger

## Build & Lint

```sh
uv sync          # install dependencies
uv run ruff check # lint (must pass before committing)
uv run ruff format --check # auto-format (fixes must be staged before committing)
uv run ty check  # type check
uv run todo-merger --help        # smoke test
```

No test suite yet. After changes, verify with `ruff check` and a `--help` invocation.

## Architecture

- **`__init__.py`** — entry point, argparse setup, Flask app factory (`create_app`), all CLI command functions (`cli_list_issues`, `cli_create_issue`, `cli_list_labels`), `main()`
- **`main.py`** — Flask blueprint with web routes (`/`, `/new`, `/ranking`, `/todolist`, etc.)
- **`_views.py`** — business logic shared between web routes and CLI (e.g. `get_issues_and_stats`, `private_tasks_repo_create_issue`)
- **`_types.py`** — `IssueItem` and `IssuesStats` dataclasses; single source of truth for issue fields
- **`_helpers.py`** — shared utilities: `sort_assignees`, `instance_id`, `convert_to_datetime`, `time_ago`
- **`_issues.py`**, **`_github.py`**, **`_gitlab.py`**, **`_gitea.py`**, **`_msplanner.py`** — per-service fetching logic
- **`_private_tasks.py`** — create/list labels for the configured private tasks repo; all create functions return `(web_url, uid)` tuples
- **`_cache.py`** — JSON-file-based cache in `platformdirs` user cache dir; per-instance files + combined cache
- **`_config.py`** — TOML config loading; `issues-config.json` stores local rank/todolist overrides keyed by uid
- **`_auth.py`** — service login helpers

## Key Conventions

**uid construction** — must match exactly across fetch and create paths:
- GitHub: `github-{issue.id}` (global integer node ID, not issue number)
- GitLab: `gitlab-{instance_id(gitlab.url)}-{issue.id}` (global ID, not per-project iid)
- Gitea: `gitea-{instance_id(gitea.url)}-{issue['id']}`
- MS Planner: `msplanner-{task_id}`

**`instance_id(url)`** — use the helper from `_helpers.py`, not inline `hashlib.md5`. Returns 6-char hex string.

**`assignee_users`** — despite the `list` type hint, `sort_assignees()` returns a `str`. Treat defensively: `isinstance(x, list)` before joining.

**Ranking** — stored only in `issues-config.json` locally; never written back to remote. `ISSUE_RANKING_TABLE = {"pin": -1, "high": 1, "normal": 5, "low": 99}`.

**Sass compilation** — `create_app()` has `skip_sass=True` to skip Dart Sass download/compile for CLI commands. Always use this for non-web entry points.

**Service logins** — `create_app()` has `skip_logins=True` to skip all API authentication (e.g. for `list --cache`). Combined with `skip_sass=True` for fully offline CLI operation.

## CLI Command Structure

```
todo-merger web [--port PORT] [-d] [stop]   # web interface
todo-merger list [--plain|--table] [--cache]
todo-merger labels
todo-merger create TITLE [--rank RANK] [--label LABEL]...
```

Global flags (`-c`, `-v`, `-vv`, `-vvv`, `--version`) precede the subcommand.

## See Also

- `CONTRIBUTING.md` — dev setup, commit message format, release process
- `README.md` — full usage reference and configuration guide
