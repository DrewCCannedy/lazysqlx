"""Modal confirmation dialog."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }
    ConfirmScreen Vertical {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    ConfirmScreen #message {
        padding-bottom: 1;
    }
    ConfirmScreen Grid {
        grid-size: 2;
        grid-gutter: 1;
        height: auto;
    }
    """

    BINDINGS = [
        ("escape", "dismiss_no", "Cancel"),
        ("y", "confirm", "Yes"),
        ("n", "dismiss_no", "No"),
    ]

    def __init__(self, message: str, *, destructive: bool = False) -> None:
        super().__init__()
        self.message = message
        self.destructive = destructive

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.message, id="message")
            with Grid():
                yield Button(
                    "Confirm (y)",
                    id="confirm",
                    variant="error" if self.destructive else "success",
                )
                yield Button("Cancel (n / esc)", id="cancel", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_dismiss_no(self) -> None:
        self.dismiss(False)
