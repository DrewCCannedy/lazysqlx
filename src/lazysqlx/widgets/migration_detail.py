"""Right-panel widget: SQL preview of the selected migration."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Label, Static

from lazysqlx.sqlx import Migration, find_migration_files


class PreviewScroll(VerticalScroll):
    """Scrollable container with vim-style keybindings for the SQL preview."""

    BINDINGS = [
        Binding("j", "scroll_down", "Down", show=False),
        Binding("k", "scroll_up", "Up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
        Binding("ctrl+d", "scroll_half_down", "Half-page down", show=False),
        Binding("ctrl+u", "scroll_half_up", "Half-page up", show=False),
    ]

    def action_scroll_half_down(self) -> None:
        self.scroll_relative(y=max(1, self.size.height // 2), animate=False)

    def action_scroll_half_up(self) -> None:
        self.scroll_relative(y=-max(1, self.size.height // 2), animate=False)


class MigrationDetail(Vertical):
    """Shows SQL contents of the selected migration. Toggleable up/down view."""

    DEFAULT_CSS = """
    MigrationDetail {
        width: 1fr;
        border: round $primary;
    }
    MigrationDetail > .title {
        background: $primary 20%;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    MigrationDetail PreviewScroll {
        padding: 0 1;
        background: transparent;
    }
    MigrationDetail PreviewScroll:focus {
        border-left: thick $accent;
    }
    """

    def __init__(self, source: Path) -> None:
        super().__init__()
        self.source = source
        self._migration: Migration | None = None
        self._direction: str = "up"  # "up" | "down"

    def compose(self) -> ComposeResult:
        yield Label("Preview", id="preview-title", classes="title")
        with PreviewScroll(id="preview-scroll"):
            yield Static("Select a migration to preview.", id="sql", expand=True)

    def focus_preview(self) -> None:
        self.query_one("#preview-scroll", PreviewScroll).focus()

    def show(self, migration: Migration | None) -> None:
        self._migration = migration
        self._refresh_preview()

    def toggle_direction(self) -> str:
        self._direction = "down" if self._direction == "up" else "up"
        self._refresh_preview()
        return self._direction

    def _refresh_preview(self) -> None:
        title = self.query_one("#preview-title", Label)
        sql = self.query_one("#sql", Static)
        scroll = self.query_one("#preview-scroll", PreviewScroll)
        scroll.scroll_home(animate=False)
        mig = self._migration
        if mig is None:
            title.update("Preview")
            sql.update("(no migration selected)")
            return

        files = find_migration_files(self.source, mig.version)
        path: Path | None = None
        header_kind = ""

        if "sql" in files:
            path = files["sql"]
            header_kind = "simple"
        elif self._direction == "down" and "down" in files:
            path = files["down"]
            header_kind = "down"
        elif "up" in files:
            path = files["up"]
            header_kind = "up"
        elif "down" in files:
            path = files["down"]
            header_kind = "down"

        if path is None:
            title.update(f"Preview — {mig.version} {mig.description}")
            sql.update("(no .sql files found on disk)")
            return

        try:
            contents = path.read_text(encoding="utf-8")
        except OSError as exc:
            sql.update(f"Failed to read {path}:\n{exc}")
            title.update(f"Preview — {path.name}")
            return

        title.update(f"Preview — {path.name} [{header_kind}] ({mig.status})")
        sql.update(contents or "(empty file)")

    @property
    def current_file(self) -> Path | None:
        if self._migration is None:
            return None
        files = find_migration_files(self.source, self._migration.version)
        if "sql" in files:
            return files["sql"]
        if self._direction == "down" and "down" in files:
            return files["down"]
        if "up" in files:
            return files["up"]
        return files.get("down")
