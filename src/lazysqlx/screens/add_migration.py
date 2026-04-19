"""Modal: prompt for new migration name and reversible flag."""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label


@dataclass
class AddMigrationResult:
    name: str
    reversible: bool


class AddMigrationScreen(ModalScreen[AddMigrationResult | None]):
    DEFAULT_CSS = """
    AddMigrationScreen {
        align: center middle;
    }
    AddMigrationScreen Vertical {
        width: 70;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    AddMigrationScreen Input {
        margin-bottom: 1;
    }
    AddMigrationScreen Grid {
        grid-size: 2;
        grid-gutter: 1;
        height: auto;
        margin-top: 1;
    }
    """

    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("New migration", id="title")
            yield Input(placeholder="name (e.g. add_users_email)", id="name")
            yield Checkbox(
                "Reversible (-r: creates .up.sql + .down.sql)", value=True, id="reversible"
            )
            with Grid():
                yield Button("Create", id="create", variant="success")
                yield Button("Cancel (esc)", id="cancel", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#name", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            self._submit()
        else:
            self.dismiss(None)

    def _submit(self) -> None:
        name = self.query_one("#name", Input).value.strip()
        if not name:
            self.app.bell()
            return
        reversible = self.query_one("#reversible", Checkbox).value
        self.dismiss(AddMigrationResult(name=name, reversible=reversible))

    def action_cancel(self) -> None:
        self.dismiss(None)
