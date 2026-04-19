"""Async wrapper around the `sqlx` CLI.

Shells out to `sqlx migrate ...` / `sqlx database ...` and parses stdout.
All commands run with `NO_COLOR=1` so status labels come through unstyled.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Status = Literal["installed", "pending", "mismatch", "unknown"]

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Example line (NO_COLOR): "20240101120000/installed create users"
# Mismatch variant:         "20240101120000/installed (different checksum) create users"
INFO_LINE_RE = re.compile(
    r"^(?P<version>\d+)/"
    r"(?P<status>installed(?: \(different checksum\))?|pending)"
    r"\s+(?P<description>.*)$"
)


@dataclass(frozen=True)
class Migration:
    version: str
    description: str
    status: Status

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    @property
    def label(self) -> str:
        marker = {
            "installed": "✓",
            "pending": " ",
            "mismatch": "!",
            "unknown": "?",
        }[self.status]
        return f"{marker} {self.version} {self.description}"


@dataclass
class CommandResult:
    ok: bool
    stdout: str
    stderr: str
    returncode: int

    @property
    def summary(self) -> str:
        msg = (self.stdout + "\n" + self.stderr).strip()
        return msg or ("ok" if self.ok else f"exit {self.returncode}")


class SqlxError(RuntimeError):
    pass


def sqlx_available() -> bool:
    return shutil.which("sqlx") is not None


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


async def _run(
    args: list[str],
    *,
    database_url: str | None,
    cwd: Path | None = None,
) -> CommandResult:
    if not sqlx_available():
        raise SqlxError("`sqlx` CLI not found on PATH. Install with `cargo install sqlx-cli`.")

    env = os.environ.copy()
    env["NO_COLOR"] = "1"
    if database_url:
        env["DATABASE_URL"] = database_url

    proc = await asyncio.create_subprocess_exec(
        "sqlx",
        *args,
        cwd=str(cwd) if cwd else None,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await proc.communicate()
    stdout = strip_ansi(stdout_b.decode("utf-8", errors="replace"))
    stderr = strip_ansi(stderr_b.decode("utf-8", errors="replace"))
    return CommandResult(
        ok=proc.returncode == 0,
        stdout=stdout,
        stderr=stderr,
        returncode=proc.returncode or 0,
    )


def parse_info(stdout: str) -> list[Migration]:
    migrations: list[Migration] = []
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = INFO_LINE_RE.match(line)
        if not m:
            continue
        status_raw = m.group("status")
        if status_raw == "pending":
            status: Status = "pending"
        elif "different checksum" in status_raw:
            status = "mismatch"
        else:
            status = "installed"
        migrations.append(
            Migration(
                version=m.group("version"),
                description=m.group("description").strip(),
                status=status,
            )
        )
    return migrations


async def migrate_info(
    source: Path, database_url: str | None
) -> tuple[list[Migration], CommandResult]:
    result = await _run(
        ["migrate", "info", "--source", str(source)],
        database_url=database_url,
    )
    return parse_info(result.stdout), result


async def migrate_run(source: Path, database_url: str | None) -> CommandResult:
    return await _run(
        ["migrate", "run", "--source", str(source)],
        database_url=database_url,
    )


async def migrate_revert(source: Path, database_url: str | None) -> CommandResult:
    return await _run(
        ["migrate", "revert", "--source", str(source)],
        database_url=database_url,
    )


async def migrate_add(name: str, *, reversible: bool, source: Path) -> CommandResult:
    args = ["migrate", "add", "--source", str(source)]
    if reversible:
        args.append("-r")
    args.append(name)
    return await _run(args, database_url=None)


async def database_drop(database_url: str | None) -> CommandResult:
    return await _run(
        ["database", "drop", "-y"],
        database_url=database_url,
    )


async def database_create(database_url: str | None) -> CommandResult:
    return await _run(["database", "create"], database_url=database_url)


async def database_reset(source: Path, database_url: str | None) -> CommandResult:
    """Equivalent to `sqlx database reset -y --source <source>`.

    `sqlx database reset` drops, creates, and runs migrations in one command.
    """
    return await _run(
        ["database", "reset", "-y", "--source", str(source)],
        database_url=database_url,
    )


def find_migration_files(source: Path, version: str) -> dict[str, Path]:
    """Locate on-disk files for a migration version.

    Returns a dict with keys like 'up', 'down', 'sql' pointing to real paths.
    - Reversible:    {version}_*.up.sql  +  {version}_*.down.sql
    - Simple:        {version}_*.sql
    """
    files: dict[str, Path] = {}
    if not source.is_dir():
        return files
    for entry in source.iterdir():
        if not entry.is_file() or not entry.name.startswith(version):
            continue
        name = entry.name
        if name.endswith(".up.sql"):
            files["up"] = entry
        elif name.endswith(".down.sql"):
            files["down"] = entry
        elif name.endswith(".sql"):
            files["sql"] = entry
    return files
