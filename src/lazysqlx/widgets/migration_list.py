"""Left-panel widget: selectable list of migrations from `sqlx migrate info`."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Label, ListItem, ListView

from lazysqlx.sqlx import Migration


class MigrationListItem(ListItem):
    def __init__(self, migration: Migration) -> None:
        super().__init__(Label(migration.label))
        self.migration = migration
        self.add_class(f"status-{migration.status}")


class MigrationListView(ListView):
    """ListView with vim-style cursor bindings."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "first", "Top", show=False),
        Binding("G", "last", "Bottom", show=False),
    ]

    def action_first(self) -> None:
        if len(self.children) > 0:
            self.index = 0

    def action_last(self) -> None:
        count = len(self.children)
        if count > 0:
            self.index = count - 1


class MigrationList(Vertical):
    """List of migrations. Emits Selected when the highlighted row changes."""

    DEFAULT_CSS = """
    MigrationList {
        width: 45%;
        min-width: 30;
        border: round $primary;
        padding: 0;
    }
    MigrationList > .title {
        background: $primary 20%;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    MigrationList ListView {
        height: 1fr;
        background: transparent;
    }
    MigrationList ListItem {
        padding: 0 1;
    }
    MigrationList .status-installed Label {
        color: $success;
    }
    MigrationList .status-pending Label {
        color: $warning;
    }
    MigrationList .status-mismatch Label {
        color: $error;
        text-style: bold;
    }
    """

    class Selected(Message):
        def __init__(self, migration: Migration | None) -> None:
            super().__init__()
            self.migration = migration

    def __init__(self) -> None:
        super().__init__()
        self._migrations: list[Migration] = []

    def compose(self) -> ComposeResult:
        yield Label("Migrations", classes="title")
        yield MigrationListView(id="migrations")

    async def set_migrations(self, migrations: list[Migration]) -> None:
        self._migrations = migrations
        list_view = self.query_one("#migrations", MigrationListView)
        prev_index = list_view.index
        await list_view.clear()
        if not migrations:
            await list_view.append(ListItem(Label("(no migrations)")))
            self.post_message(self.Selected(None))
            return
        for mig in migrations:
            await list_view.append(MigrationListItem(mig))
        # First load (prev_index is None): land on the newest migration — the one
        # you're most likely about to touch. Refresh: preserve the prior cursor.
        target = len(migrations) - 1 if prev_index is None else min(prev_index, len(migrations) - 1)
        list_view.index = target
        self.post_message(self.Selected(migrations[target]))

    @property
    def selected(self) -> Migration | None:
        list_view = self.query_one("#migrations", MigrationListView)
        idx = list_view.index
        if idx is None or idx >= len(self._migrations):
            return None
        return self._migrations[idx]

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        event.stop()
        item = event.item
        if isinstance(item, MigrationListItem):
            self.post_message(self.Selected(item.migration))
        else:
            self.post_message(self.Selected(None))

    def focus_list(self) -> None:
        self.query_one("#migrations", ListView).focus()

    def jump_to(self, index: int) -> None:
        list_view = self.query_one("#migrations", MigrationListView)
        count = len(self._migrations)
        if count == 0:
            return
        list_view.index = max(0, min(index, count - 1))
