# lazysqlx

A lazygit-inspired TUI for [sqlx](https://github.com/launchbadge/sqlx) database migrations.

## Install

Install the CLI as a globally-available tool with uv:

```sh
uv tool install git+https://github.com/DrewCCannedy/lazysqlx     # from GitHub
uv tool install lazysqlx                                          # from PyPI (once published)
uv tool install ~/projects/lazysqlx                               # from a local checkout
uv tool install -e ~/projects/lazysqlx                            # editable: tracks the checkout
```

After edits to a non-editable local install, re-sync with:

```sh
uv tool install --reinstall <same-source-as-above>
```

Or run from source without installing:

```sh
git clone https://github.com/DrewCCannedy/lazysqlx
cd lazysqlx
uv sync
uv run lazysqlx
```

Requires the `sqlx` CLI on your `PATH`:

```sh
cargo install sqlx-cli
# or, smaller install with just the backends you need:
cargo install sqlx-cli --no-default-features --features rustls,sqlite,postgres
```

## Usage

```sh
lazysqlx                                          # auto-discovers a 'migrations' dir (≤3 levels deep)
lazysqlx --source ./db/migrations                 # explicit path skips discovery
lazysqlx --max-depth 5                            # search deeper
lazysqlx --database-url sqlite://./dev.db --source ./migrations
```

By default, `lazysqlx` walks the current directory up to `--max-depth` levels
(default `3`) looking for folders named `migrations`. Common noise dirs
(`.git`, `node_modules`, `.venv`, `target`, etc.) are skipped. If several are
found, the shallowest wins and the rest are listed on stderr — pass
`--source` to pin a specific one. `DATABASE_URL` falls back to the
environment or a `.env` in the CWD.

## Try it locally with SQLite

The repo ships with example migrations for a `posts` + `comments` schema
under `./migrations/`. To kick the tires without standing up Postgres:

```sh
# from the repo root
export DATABASE_URL=sqlite://./dev.db             # any path works; this one is gitignored
sqlx database create                              # creates dev.db
uv run lazysqlx                                   # auto-discovers ./migrations
```

If you'd rather not export `DATABASE_URL`, pass it inline:

```sh
uv run lazysqlx --database-url sqlite://./dev.db
```

To start from a clean slate, delete `dev.db` and re-run `sqlx database create`
(or just hit `d` inside the TUI — that drops, recreates, and re-runs all
migrations in one go).

Then inside the TUI: `r` to run all pending, `R` to revert the last one,
`u` to flip between up/down SQL, `d` to drop + recreate + rerun.

## Developing

One-time setup after cloning:

```sh
uv sync --group dev                               # installs pre-commit + ruff
uv run pre-commit install                         # registers the git hook
```

From then on, `git commit` auto-formats and lints staged files:

- **Python** — `ruff` (lint + `--fix`) and `ruff-format` (black-style).
- **Lua** — `stylua` (column 100, 2-space indent; see `stylua.toml`).
- **Hygiene** — trailing whitespace, end-of-file, YAML/TOML syntax, large-file guard (≤1 MB).

Run everything manually against the whole tree:

```sh
uv run pre-commit run --all-files
```

Bump pinned hook versions:

```sh
uv run pre-commit autoupdate
```

## Keybindings

Vim-flavored. Destructive actions are Shift-variants so they don't trip
on vim muscle memory.

### Actions

| Key            | Action                                                  |
| -------------- | ------------------------------------------------------- |
| `o`            | New migration ("open below")                            |
| `r`            | Run all pending migrations (confirm)                    |
| `R`            | Revert last migration (confirm)                         |
| `d`            | Delete selected migration files (pending only; confirm) |
| `D`            | Database reset: drop + create + run (confirm)           |
| `e` / `⏎`      | Edit selected migration file                            |
| `⇥` Tab        | Toggle up/down SQL in preview                           |
| `q`            | Quit                                                    |

### Navigation

| Key                | Action                                    |
| ------------------ | ----------------------------------------- |
| `j` / `k`, ↑/↓     | Next / prev migration                     |
| `h` / `l`          | Focus list / focus preview                |
| `g` / `G`          | Jump to first / last migration            |
| `⌃d` / `⌃u`        | Half-page scroll (preview pane)           |
| `⌃r` / `F5`        | Refresh migration list                    |

`d` is only valid on `pending` migrations — deleting a migration whose
schema is already applied would leave the DB tracking a ghost. Revert
with `R` first.

## Neovim integration

### Plain `:terminal`

Launched from a Neovim `:terminal`, pressing `e` opens the migration file in a
new tab of the parent Neovim (via `nvim --server $NVIM --remote-tab`) without
suspending the TUI. Outside Neovim, `$EDITOR` is used (falls back to `vi`).

### Floating terminal plugin (`lazysqlx.nvim`)

This repo doubles as a Neovim plugin. Install with lazy.nvim from GitHub:

```lua
-- ~/.config/nvim/lua/plugins/lazysqlx.lua  (LazyVim layout)
return {
  {
    -- Label the <leader>m prefix in the which-key popup.
    "folke/which-key.nvim",
    opts = {
      spec = {
        { "<leader>m", group = "migrations", icon = { icon = "󰆼", color = "cyan" } },
      },
    },
  },
  {
    "DrewCCannedy/lazysqlx",                    -- or your fork/path
    cmd = { "LazySqlx", "LazySqlxToggle" },
    keys = {
      {
        "<leader>mm",
        "<cmd>LazySqlx<cr>",
        desc = "lazysqlx",
        icon = { icon = "󰆼", color = "cyan" },
      },
    },
    opts = {},                                  -- calls require("lazysqlx").setup({})
  },
}
```

Or from a local checkout (useful while hacking on the plugin itself):

```lua
-- ~/.config/nvim/lua/plugins/lazysqlx.lua
return {
  {
    "folke/which-key.nvim",
    opts = {
      spec = {
        { "<leader>m", group = "migrations", icon = { icon = "󰆼", color = "cyan" } },
      },
    },
  },
  {
    dir = "~/projects/lazysqlx",                -- path to your checkout
    name = "lazysqlx",
    cmd = { "LazySqlx", "LazySqlxToggle" },
    keys = {
      {
        "<leader>mm",
        "<cmd>LazySqlx<cr>",
        desc = "lazysqlx",
        icon = { icon = "󰆼", color = "cyan" },
      },
    },
    opts = {},
  },
}
```

Restart Neovim (or `:Lazy sync`), then run `:checkhealth lazysqlx` to verify
that the `lazysqlx` and `sqlx` binaries are on `PATH`.

With LazyVim, pressing `<leader>` will show `migrations` as a labelled
group, with `lazysqlx` inside when you continue with `m`. The group label
has to be registered on which-key's `opts.spec` — lazy.nvim's `keys`
entries alone don't feed group-only entries through to which-key v3.
`<leader>mm` stays out of LazyVim's `<leader>g` git group; pick any
mapping you like.

You still need the `lazysqlx` binary on `PATH` (see [Install](#install) above)
and the `sqlx` CLI.

Commands:

- `:LazySqlx [args...]` — open the TUI in a centered floating terminal; extra
  args are forwarded, e.g. `:LazySqlx --source ./db/migrations`
- `:LazySqlxToggle [args...]` — toggle it

Inside the float, pressing `e` closes the float and opens the migration in a
new tab — same flow as lazygit.nvim.

Configuration defaults (pass overrides to `opts`):

```lua
{
  cmd = "lazysqlx",     -- binary name
  args = {},            -- extra args, e.g. { "--source", "./db/migrations" }
  width = 0.85,         -- fraction of &columns
  height = 0.85,        -- fraction of &lines
  border = "rounded",   -- any nvim_open_win border style
  title = " lazysqlx ",
  title_pos = "center",
}
```
