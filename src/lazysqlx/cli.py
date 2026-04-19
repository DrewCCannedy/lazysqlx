"""Command-line entry point."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from lazysqlx import __version__

_DISCOVERY_SKIP = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "target",
        "venv",
    }
)


def _find_migrations_dirs(root: Path, max_depth: int) -> list[Path]:
    """Locate directories named `migrations` up to `max_depth` below `root`.

    Depth 0 is `root` itself. Skips common noise dirs (VCS, build outputs,
    virtualenvs, `node_modules`, etc.) and does not recurse into a matched
    `migrations` dir.
    """
    matches: list[Path] = []

    def walk(d: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(d.iterdir())
        except OSError:
            return
        for entry in entries:
            if not entry.is_dir():
                continue
            if entry.name == "migrations":
                matches.append(entry)
                continue
            if entry.name.startswith(".") or entry.name in _DISCOVERY_SKIP:
                continue
            walk(entry, depth + 1)

    walk(root.resolve(), 0)
    return matches


def _load_dotenv(path: Path) -> None:
    """Minimal `.env` loader. Matches sqlx's KEY=VALUE line format.

    We deliberately don't pull in python-dotenv — sqlx itself only supports
    the simple KEY=VALUE format, and we want parity, not a richer parser.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lazysqlx",
        description="lazygit-inspired TUI for sqlx migrations",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="Migrations directory (default: auto-discover a 'migrations' "
        "folder up to --max-depth levels below the CWD)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Max directory depth to search when auto-discovering migrations "
        "(default: 3; ignored if --source is given)",
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Database URL (sqlx-supported: sqlite://, postgres://, mysql://); "
        "falls back to DATABASE_URL / .env",
    )
    parser.add_argument("--version", action="version", version=f"lazysqlx {__version__}")
    args = parser.parse_args(argv)

    _load_dotenv(Path.cwd() / ".env")
    database_url = args.database_url or os.environ.get("DATABASE_URL")

    if args.source is not None:
        source = args.source
        if not source.exists():
            print(
                f"error: migrations directory {source} does not exist",
                file=sys.stderr,
            )
            return 2
    else:
        matches = _find_migrations_dirs(Path.cwd(), args.max_depth)
        if not matches:
            print(
                f"error: no 'migrations' directory found within "
                f"{args.max_depth} levels of {Path.cwd()}.\n"
                f"       pass --source explicitly, or raise --max-depth.",
                file=sys.stderr,
            )
            return 2
        matches.sort(key=lambda p: (len(p.parts), str(p)))
        source = matches[0]
        if len(matches) > 1:
            print(f"note: {len(matches)} 'migrations' dirs found, using {source}", file=sys.stderr)
            for extra in matches[1:]:
                print(f"      also: {extra}", file=sys.stderr)

    # Imported lazily so `--help` / `--version` don't pay Textual's import cost.
    from lazysqlx.app import LazySqlxApp

    app = LazySqlxApp(source=source.resolve(), database_url=database_url)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
