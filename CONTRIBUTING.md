# Contributing

First of all, thank you for considering contributing to this project!

## Some Ceremonial Stuff

Run `uv sync --group dev` and then `uv run pre-commit install` before starting any work. This wires up the `ruff`, `stylua`, and hygiene hooks on `git commit`.

Before you start any work, make sure you have an issue open, and have it assigned to yourself.

This will stop two people from working on the same issue, and will also give us a place to discuss the implementation details of your contribution.

If you want to contribute, please open an issue first.

There is a chance your feature doesn't align with the vision of the project.
We want to avoid you doing work that might not be used.

## Git Workflow

1. Fork the repository
2. Create your feature/bugfix branch: `git checkout -b feature-123/your-feature`
   a. The 123 numbers should represent the issue you are working on.
3. When committing, use the [conventional commit format](https://www.conventionalcommits.org/en/v1.0.0/).
   - You can use `git log` for examples of previous commit messages.
   - Please try to have an understandable and followable commit history, open a new branch (don't PR changes from your main to the repository's main).
4. Before opening a PR, run the pre-commit hooks against the whole tree and make sure the TUI still launches:

   ```bash
   uv run pre-commit run --all-files
   uv run lazysqlx --source ./migrations        # from repo root, with DATABASE_URL set
   ```
5. Open a PR to `main`.

## Packages and Their Responsibilities

- `src/lazysqlx/cli.py` — argument parsing, migrations-dir discovery, environment bootstrapping.
- `src/lazysqlx/sqlx.py` — thin wrapper around the `sqlx` CLI; parses `migrate info` and runs `migrate run/revert/database drop|create`.
- `src/lazysqlx/app.py` — the Textual `App` subclass: global keybindings, layout, and orchestration between the list and detail widgets.
- `src/lazysqlx/widgets/` — `MigrationList` (left pane) and `MigrationDetail` (right pane). Each owns its own CSS and vim-style bindings.
- `lua/lazysqlx/` and `plugin/lazysqlx.lua` — the Neovim plugin: floating-terminal launcher, `:checkhealth`, and the `remote-send` editor handoff that closes the float and opens the migration in a new tab.

## Testing

There is no automated test suite yet — changes are verified by exercising the TUI against the example migrations under `./migrations/` with a local SQLite database (see README: "Try it locally with SQLite").

If you are making complex or significant changes, please consider adding tests. Python code should be tested with `pytest`; Textual provides a `Pilot` harness for driving the TUI in headless tests.

At minimum, before opening a PR please:

- Run `uv run pre-commit run --all-files` — this formats + lints Python with `ruff` and Lua with `stylua`.
- Manually smoke-test the TUI path you touched against `./migrations/` with a throwaway SQLite database.
- If you touched the Neovim plugin, run `:checkhealth lazysqlx` and verify `:LazySqlx` still opens a floating terminal.
