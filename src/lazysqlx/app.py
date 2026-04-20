"""Main Textual app: wires layout, keybindings, and sqlx actions."""

from __future__ import annotations

from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header

from lazysqlx import sqlx as sqlx_mod
from lazysqlx.editor import open_file
from lazysqlx.screens.add_migration import AddMigrationResult, AddMigrationScreen
from lazysqlx.screens.confirm import ConfirmScreen
from lazysqlx.sqlx import CommandResult, Migration, SqlxError
from lazysqlx.widgets.migration_detail import MigrationDetail
from lazysqlx.widgets.migration_list import MigrationList


class LazySqlxApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    #body {
        height: 1fr;
    }
    """

    BINDINGS = [
        # Actions (shown in footer)
        Binding("o", "add", "New"),
        Binding("r", "run", "Run"),
        Binding("R", "revert", "Revert"),
        Binding("d", "delete", "Delete"),
        Binding("D", "db_reset", "DB reset"),
        Binding("e", "edit", "Edit"),
        Binding("tab", "toggle_direction", "up/down", priority=True),
        Binding("q", "quit", "Quit"),
        # Navigation & aliases (hidden from footer)
        Binding("h", "focus_list", "Focus list", show=False),
        Binding("l", "focus_preview", "Focus preview", show=False),
        Binding("enter", "edit", "Edit", show=False),
        Binding("ctrl+r", "refresh", "Refresh", show=False),
        Binding("f5", "refresh", "Refresh", show=False),
    ]

    def __init__(self, source: Path, database_url: str | None) -> None:
        super().__init__()
        self.source = source
        self.database_url = database_url
        self._selected: Migration | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="body"):
            yield MigrationList()
            yield MigrationDetail(self.source)
        yield Footer()

    async def on_mount(self) -> None:
        self.title = "lazysqlx"
        self.sub_title = str(self.source)
        await self.action_refresh()
        self.query_one(MigrationList).focus_list()

    # ---------- helpers ------------------------------------------------

    async def _refresh_migrations(self) -> None:
        try:
            migrations, result = await sqlx_mod.migrate_info(self.source, self.database_url)
        except SqlxError as exc:
            self.notify(str(exc), severity="error", timeout=8)
            return

        if not result.ok:
            self.notify(
                f"sqlx migrate info failed: {result.summary}",
                severity="error",
                timeout=8,
            )
            # Still try to show what we parsed (may be empty).

        list_widget = self.query_one(MigrationList)
        await list_widget.set_migrations(migrations)

    def _report(self, action: str, result: CommandResult) -> None:
        if result.ok:
            msg = result.summary if result.stdout.strip() else f"{action}: ok"
            self.notify(msg, timeout=6)
        else:
            self.notify(
                f"{action} failed:\n{result.summary}",
                severity="error",
                timeout=10,
            )

    async def _confirm(self, message: str, *, destructive: bool = False) -> bool:
        return bool(await self.push_screen_wait(ConfirmScreen(message, destructive=destructive)))

    # ---------- message handlers --------------------------------------

    def on_migration_list_selected(self, event: MigrationList.Selected) -> None:
        self._selected = event.migration
        self.query_one(MigrationDetail).show(event.migration)

    # ---------- actions ------------------------------------------------

    async def action_refresh(self) -> None:
        await self._refresh_migrations()

    def action_focus_list(self) -> None:
        self.query_one(MigrationList).focus_list()

    def action_focus_preview(self) -> None:
        self.query_one(MigrationDetail).focus_preview()

    @work
    async def action_add(self) -> None:
        result = await self.push_screen_wait(AddMigrationScreen())
        if not isinstance(result, AddMigrationResult):
            return
        try:
            cmd = await sqlx_mod.migrate_add(
                result.name, reversible=result.reversible, source=self.source
            )
        except SqlxError as exc:
            self.notify(str(exc), severity="error")
            return
        self._report("add", cmd)
        await self._refresh_migrations()

    @work
    async def action_run(self) -> None:
        if not await self._confirm("Run all pending migrations?"):
            return
        try:
            cmd = await sqlx_mod.migrate_run(self.source, self.database_url)
        except SqlxError as exc:
            self.notify(str(exc), severity="error")
            return
        self._report("run", cmd)
        await self._refresh_migrations()

    @work
    async def action_revert(self) -> None:
        if not await self._confirm("Revert the most recently applied migration?", destructive=True):
            return
        try:
            cmd = await sqlx_mod.migrate_revert(self.source, self.database_url)
        except SqlxError as exc:
            self.notify(str(exc), severity="error")
            return
        self._report("revert", cmd)
        await self._refresh_migrations()

    @work
    async def action_delete(self) -> None:
        mig = self._selected
        if mig is None:
            self.notify("No migration selected.", severity="warning")
            return
        if not mig.is_pending:
            self.notify(
                f"Can only delete pending migrations (this one is {mig.status}). "
                "Revert it first with `R`.",
                severity="warning",
                timeout=6,
            )
            return
        files = sqlx_mod.find_migration_files(self.source, mig.version)
        if not files:
            self.notify("No files to delete.", severity="warning")
            return
        names = "\n  ".join(p.name for p in files.values())
        if not await self._confirm(f"Delete these files?\n  {names}", destructive=True):
            return
        deleted = 0
        for path in files.values():
            try:
                path.unlink()
                deleted += 1
            except OSError as exc:
                self.notify(f"Failed to delete {path.name}: {exc}", severity="error")
                break
        if deleted:
            self.notify(f"Deleted {deleted} file(s).", timeout=4)
        await self._refresh_migrations()

    @work
    async def action_db_reset(self) -> None:
        if not await self._confirm(
            "DROP the database, recreate it, and run all migrations?\n" "This destroys all data.",
            destructive=True,
        ):
            return
        try:
            cmd = await sqlx_mod.database_reset(self.source, self.database_url)
        except SqlxError as exc:
            self.notify(str(exc), severity="error")
            return
        self._report("database reset", cmd)
        await self._refresh_migrations()

    def action_edit(self) -> None:
        detail = self.query_one(MigrationDetail)
        path = detail.current_file
        if path is None:
            self.notify("No file to edit.", severity="warning")
            return
        open_file(self, path)
        # After returning, re-render in case contents changed.
        detail.show(self._selected)

    def action_toggle_direction(self) -> None:
        direction = self.query_one(MigrationDetail).toggle_direction()
        self.notify(f"Showing {direction}.sql", timeout=3)
