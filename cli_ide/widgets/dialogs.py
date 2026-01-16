"""Dialog widgets for CLI-IDE."""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class SaveConfirmDialog(ModalScreen[str]):
    """Dialog to confirm saving modified file."""

    CSS = """
    SaveConfirmDialog {
        align: center middle;
    }

    #dialog {
        width: 60;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    #buttons {
        margin-top: 1;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, filename: str):
        super().__init__()
        self.filename = filename

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(f"'{self.filename}' has been modified.")
            yield Label("Do you want to save changes?")
            with Horizontal(id="buttons"):
                yield Button("Save", id="save", variant="primary")
                yield Button("Don't Save", id="dont-save", variant="warning")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id)
