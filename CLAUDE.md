# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

- `uv sync` — install runtime dependencies into `.venv/`.
- `uv sync --group dev` — also install `pre-commit` + `ruff` dev tooling.
- `uv run pre-commit install` — one-time, registers the git hook so commits auto-lint/format.
- `uv run pre-commit run --all-files` — run ruff (lint + format), stylua, and hygiene hooks across the whole tree.
- `uv run lazysqlx [--source PATH] [--max-depth N] [--database-url ...]` — run the TUI from source.
- `uv run python -m lazysqlx` — equivalent entry point via `__main__`.
- Install globally for Neovim to find: `uv tool install ~/projects/lazysqlx` (add `--reinstall` after edits, or `-e` for editable).
- Local SQLite smoke test (from repo root): `export DATABASE_URL=sqlite://./dev.db && sqlx database create && uv run lazysqlx`. The bundled `./migrations/` (posts + comments + add_published) is auto-discovered. `dev.db` is gitignored.
- No test suite is configured. Changes to `sqlx.py` parsing or subprocess flags should be hand-verified against `./migrations/`.

The `sqlx` CLI (`cargo install sqlx-cli`) must be on `PATH` at runtime — `sqlx_available()` in `src/lazysqlx/sqlx.py` guards against this and raises `SqlxError`.

## Architecture

This repo is simultaneously **a Python TUI package** and **a Neovim plugin**. The top-level `lua/` and `plugin/` directories exist so the repo can be installed directly by lazy.nvim (`"DrewCCannedy/lazysqlx"`), while `src/lazysqlx/` ships to PyPI. They communicate over environment variables and `nvim --server --remote-send`, not a shared file format.

### TUI layer (`src/lazysqlx/`)

- **`sqlx.py`** is the only module that shells out. Every subprocess runs with `NO_COLOR=1` and its stdout is passed through `strip_ansi()` before `INFO_LINE_RE` parses `migrate info` output into `Migration` dataclasses. If you change sqlx invocations or parse output, update both the regex and `parse_info` — the TUI has no other source of migration state. Status is one of `installed | pending | mismatch | unknown`; mismatch is detected from the literal `(different checksum)` marker sqlx emits.
- **`app.py`** (`LazySqlxApp`) wires everything: it owns `source: Path` and `database_url: str | None`, composes `MigrationList` + `MigrationDetail` side-by-side, and dispatches keybindings to `action_*` methods. Actions that open a modal (`add`, `run`, `revert`, `db_reset`, `delete`) are decorated `@work` so they can `await self.push_screen_wait(...)`; plain actions (`edit`, `toggle_direction`, `focus_*`, `first`, `last`) are sync. After every mutating sqlx call, actions call `_refresh_migrations()` to re-query `migrate info`.
- **Keybindings are vim-flavored.** Actions: `o` new (was `a`), `r` run, `R` revert, `d` delete (pending-only — refuses on installed/mismatch, unlinks files via `find_migration_files`), `D` db-reset (was `d`), `e`/`⏎` edit, `<Tab>` toggle direction (was `u`/`w`). Navigation: `h`/`l` pane focus, `g`/`G` first/last, `<C-d>`/`<C-u>` half-page scroll. Shift-variants are the destructive-action convention (`R`, `D`) — do not add single-letter destructive bindings. When adding a new action, decide show/hide in the footer via `Binding(..., show=...)`: actions visible, aliases + navigation hidden.
- **Widgets emit messages, don't reach across.** `MigrationList.Selected` is the only channel from list → detail; `app.py` forwards via `on_migration_list_selected`. Don't bypass this — `MigrationDetail.show()` is how the preview stays in sync with the list.
- **Initial cursor lands on the newest migration**, not the oldest. `MigrationList.set_migrations` detects first load via `list_view.index is None` and sets the target to `len(migrations) - 1`; subsequent calls (refresh) preserve the prior index clamped to the new length. Reason: after `sqlx migrate add`, the user almost always wants to act on the migration they just created. Don't "fix" this to default to index 0.
- **The preview is a focusable `PreviewScroll`** (subclass of `VerticalScroll` inside `MigrationDetail`) with its own vim bindings (`j`/`k`/`g`/`G`/`<C-d>`/`<C-u>`). Focus is switched via `app.py`'s `action_focus_list` / `action_focus_preview` (`h` / `l`). When a new migration is shown, `_refresh_preview` resets the scroll to the top so you don't inherit scroll state from the previous file.
- **File discovery for previews** lives in `sqlx.find_migration_files()`. It recognizes sqlx's two layouts: reversible (`{version}_*.up.sql` + `.down.sql`) and simple (`{version}_*.sql`). `MigrationDetail` falls back up → down when the user-selected direction is unavailable, and simple migrations ignore the toggle entirely.

### Editor handoff (`editor.py`)

Three mutually exclusive paths, checked in order:

1. **`LAZYSQLX_NVIM_FLOAT=1` + `$NVIM` set** — launched by the Neovim plugin's floating terminal. Sends `<C-\\><C-n>:lua require("lazysqlx").on_edit(...)<CR>` over `--remote-send`; the Lua side closes the float (killing this process) and `tabedit`s the file. No `notify()` after the send — the TUI is about to die.
2. **Only `$NVIM` set** — plain `:terminal` inside Neovim. Uses `--remote-tab` to open a new tab in the parent; TUI keeps running.
3. **Neither** — `app.suspend()` + spawn `$EDITOR` (fallback `vi`).

If you add a new editor integration, follow this pattern: detect via env vars, never block the TUI thread unless suspending.

### Neovim plugin (`lua/lazysqlx/` + `plugin/lazysqlx.lua`)

- `plugin/lazysqlx.lua` registers `:LazySqlx` and `:LazySqlxToggle` with `nargs = "*"` — extra args are forwarded to the binary via `opts.fargs`.
- `lua/lazysqlx/init.lua` owns a single floating-window state (`M.state = { buf, win, job }`). It spawns the `lazysqlx` binary with `LAZYSQLX_NVIM_FLOAT=1` using `vim.fn.jobstart(cmd, { term = true, ... })` on Neovim 0.10+ and falls back to `vim.fn.termopen` on older versions.
- `M.open(opts)` / `M.toggle(opts)` accept `{ args = {...} }` to extend `config.args` per invocation — this is the integration point for picker extensions. Keep the signature stable.
- `M.on_edit(filepath)` is the callback invoked by the Python side's `remote-send`. Keep this signature stable; changing it breaks the `editor.py` → plugin contract.
- `lua/lazysqlx/health.lua` implements `:checkhealth lazysqlx`. It checks Neovim version, `lazysqlx` + `sqlx` + `nvim` on PATH, and reports `DATABASE_URL` status. If you add a new runtime requirement, add a check here too.

### Lint & format (`.pre-commit-config.yaml` + `pyproject.toml` + `stylua.toml`)

- Dev dependencies live in `[dependency-groups].dev` in `pyproject.toml` (PEP 735). Install with `uv sync --group dev` — don't add them as runtime deps.
- `ruff` config lives in `[tool.ruff]` / `[tool.ruff.lint]`. Selected rule groups: `E`, `F`, `W`, `I`, `UP`, `B`, `SIM`. `E501` is ignored because the formatter already handles line length. `__init__.py` re-exports are exempt from `F401`.
- `stylua.toml` pins column width 100, 2-space indent, AutoPreferDouble quotes — match this style when adding Lua.
- Bump hook versions with `uv run pre-commit autoupdate`; don't hand-edit pins unless you have a reason.
- The pre-commit hook is installed via `uv run pre-commit install` (one-time per clone). There is no auto-install on `uv sync` — document it in the README's Developing section, don't try to hide it behind a magic hook.

### CLI entry (`cli.py`)

- `_load_dotenv()` is a deliberately minimal KEY=VALUE parser to match sqlx's own `.env` handling — don't swap in `python-dotenv`.
- Textual imports are lazy (inside `main()`) so `--help` / `--version` stay fast.
- `--source` defaults to `None`; when omitted, `_find_migrations_dirs()` walks the CWD up to `--max-depth` levels (default `3`) looking for dirs named `migrations`. Shallowest match wins; extras are printed to stderr. The `_DISCOVERY_SKIP` set (`.git`, `node_modules`, `.venv`, `target`, `__pycache__`, build/dist, etc.) is how we avoid walking into VCS/build noise — extend it if new ecosystems need to be ignored. Do not recurse into a matched `migrations/` itself.
