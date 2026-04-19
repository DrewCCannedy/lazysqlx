"""Open a file in the user's editor.

Three modes:
  * If `$LAZYSQLX_NVIM_FLOAT=1` is set (launched via the lazysqlx.nvim
    plugin's floating terminal), use `nvim --server $NVIM --remote-send`
    to invoke `require('lazysqlx').on_edit(<file>)` — that closes the
    float (killing this process) and opens the file in a new tab.
  * Else if `$NVIM` is set (we're in a plain Neovim `:terminal`), use
    `nvim --server $NVIM --remote-tab <file>` — opens a new tab in the
    parent Neovim without suspending the TUI.
  * Otherwise, suspend the Textual app and spawn `$EDITOR` (or `vi`).
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from textual.app import App


def open_file(app: App, filepath: Path) -> None:
    nvim_addr = os.environ.get("NVIM")
    in_float = os.environ.get("LAZYSQLX_NVIM_FLOAT") == "1"

    if nvim_addr and in_float:
        # Close the float and open the file atomically via the plugin's
        # on_edit callback. <C-\><C-n> first to drop out of terminal mode.
        keys = f'<C-\\><C-n>:lua require("lazysqlx").on_edit([[{filepath}]])<CR>'
        try:
            subprocess.run(
                ["nvim", "--server", nvim_addr, "--remote-send", keys],
                check=False,
            )
            # No notify: this process is about to be killed by the float
            # closing. Any notify would be invisible.
        except FileNotFoundError:
            app.notify("nvim not on PATH; falling back to $EDITOR", severity="warning")
            _suspend_and_edit(app, filepath)
        return

    if nvim_addr:
        try:
            subprocess.run(
                ["nvim", "--server", nvim_addr, "--remote-tab", str(filepath)],
                check=False,
            )
            app.notify(f"Opened {filepath.name} in parent nvim")
        except FileNotFoundError:
            app.notify("nvim not on PATH; falling back to $EDITOR", severity="warning")
            _suspend_and_edit(app, filepath)
        return

    _suspend_and_edit(app, filepath)


def _suspend_and_edit(app: App, filepath: Path) -> None:
    editor = os.environ.get("EDITOR", "vi")
    cmd = shlex.split(editor) + [str(filepath)]
    with app.suspend():
        subprocess.run(cmd, check=False)
