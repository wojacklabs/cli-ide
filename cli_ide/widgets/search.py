"""Search widgets for CLI-IDE."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

from rich.text import Text
from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class SearchInput(Input):
    """Custom Input that notifies parent on Enter key."""

    class EnterPressed(Message):
        """Message when Enter is pressed."""

        def __init__(self, value: str):
            super().__init__()
            self.value = value

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            self.post_message(self.EnterPressed(self.value))
            event.stop()
            event.prevent_default()
        else:
            await super()._on_key(event)


class SearchBar(Container):
    """Inline search bar for find in file."""

    can_focus = True

    class SearchSubmitted(Message):
        """Message when search is submitted."""

        def __init__(self, query: str, direction: str = "next"):
            super().__init__()
            self.query = query
            self.direction = direction

    class SearchClosed(Message):
        """Message when search bar is closed."""

        pass

    def compose(self) -> ComposeResult:
        with Horizontal(id="search-bar-content"):
            yield SearchInput(id="search-input", placeholder="Find...")
            yield Button("↑", id="find-prev", classes="search-btn")
            yield Button("↓", id="find-next", classes="search-btn")
            yield Button("✕", id="close-search", classes="search-btn")
            yield Static("", id="search-status")

    def focus_input(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", SearchInput).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-search":
            self.post_message(self.SearchClosed())
        elif event.button.id in ("find-next", "find-prev"):
            query = self.query_one("#search-input", SearchInput).value
            if query:
                direction = "next" if event.button.id == "find-next" else "prev"
                self.post_message(self.SearchSubmitted(query, direction))

    def on_search_input_enter_pressed(self, event: SearchInput.EnterPressed) -> None:
        """Handle Enter key in search input - find next match."""
        if event.value:
            self.post_message(self.SearchSubmitted(event.value, "next"))

    @on(Input.Changed, "#search-input")
    def _on_search_changed(self, event: Input.Changed) -> None:
        """Handle text change - find first match."""
        query = event.value
        if query:
            self.post_message(self.SearchSubmitted(query, "first"))

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.post_message(self.SearchClosed())
            event.stop()

    def set_status(self, text: str) -> None:
        self.query_one("#search-status", Static).update(text)

    def set_query(self, text: str) -> None:
        self.query_one("#search-input", SearchInput).value = text
        self.focus_input()


class SearchResultItem(Static):
    """A search result item that can expand to show code preview."""

    can_focus = True

    class Selected(Message):
        """Message when item is selected (double-click or enter)."""

        def __init__(self, filepath: str, line_num: int):
            super().__init__()
            self.filepath = filepath
            self.line_num = line_num

    def __init__(
        self,
        filepath: str,
        line_num: int,
        content: str,
        rel_path: str,
        root_path: Path,
        result_idx: int,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.filepath = filepath
        self.line_num = line_num
        self.content = content
        self.rel_path = rel_path
        self.root_path = root_path
        self.result_idx = result_idx
        self.expanded = False
        self._preview_lines: list[str] = []

    def render(self) -> Text:
        text = Text()
        icon = "▼ " if self.expanded else "▶ "
        text.append(icon, style="bold")
        text.append(self.rel_path, style="cyan")
        text.append(f":{self.line_num}", style="yellow")
        text.append(f" {self.content.strip()[:40]}")

        if self.expanded and self._preview_lines:
            text.append("\n")
            for i, line in enumerate(self._preview_lines):
                line_no = self.line_num - 5 + i
                if line_no == self.line_num:
                    text.append(f"  → {line_no:4d} │ ", style="bold yellow")
                    text.append(f"{line}\n", style="bold")
                else:
                    text.append(f"    {line_no:4d} │ ", style="dim")
                    text.append(f"{line}\n")

        return text

    def toggle_expand(self) -> None:
        """Toggle expanded state and load preview if needed."""
        self.expanded = not self.expanded
        if self.expanded and not self._preview_lines:
            self._load_preview()
        if self.expanded:
            self.styles.height = len(self._preview_lines) + 1
        else:
            self.styles.height = 1
        self.refresh()

    def _load_preview(self) -> None:
        """Load 5 lines before and after the match."""
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                all_lines = f.readlines()

            start = max(0, self.line_num - 6)
            end = min(len(all_lines), self.line_num + 5)

            self._preview_lines = []
            for i in range(start, end):
                line = all_lines[i].rstrip()[:70]
                self._preview_lines.append(line)
        except Exception:
            self._preview_lines = ["  (Unable to load preview)"]

    def on_click(self, event: events.Click) -> None:
        """Handle click - header toggles expand, preview area opens file."""
        if self.expanded and event.y > 0:
            self.post_message(self.Selected(self.filepath, self.line_num))
        else:
            self.toggle_expand()

    def on_key(self, event: events.Key) -> None:
        """Handle Enter key to open file."""
        if event.key == "enter":
            self.post_message(self.Selected(self.filepath, self.line_num))
            event.stop()


class ProjectSearchDialog(ModalScreen[str]):
    """Dialog for searching text across project files."""

    BINDINGS = [
        Binding("enter", "do_search", "Search", show=False, priority=True),
        Binding("escape", "close_dialog", "Close", show=False, priority=True),
    ]

    CSS = """
    ProjectSearchDialog {
        align: center middle;
        background: $background 50%;
    }

    #project-search-dialog {
        width: 90;
        height: 28;
        border: solid $primary;
        background: $surface;
    }

    #project-search-header {
        height: 3;
        padding: 0 1;
        background: $primary;
    }

    #project-search-header Label {
        width: auto;
        padding: 1;
    }

    #project-search-input {
        width: 1fr;
        height: 3;
    }

    #project-search-results {
        height: 1fr;
        margin: 0 1;
        border: solid $primary-darken-2;
        overflow-y: auto;
    }

    #project-search-results SearchResultItem {
        width: 100%;
        padding: 0 1;
        border-bottom: solid $primary-darken-3;
    }

    #project-search-results SearchResultItem:hover {
        background: $boost;
    }

    #project-search-footer {
        height: 3;
        padding: 0 1;
        align: left middle;
    }

    #result-count {
        width: 1fr;
    }

    #close-project-search {
        width: 12;
    }

    #open-file-btn {
        width: 15;
        margin-right: 1;
    }
    """

    def __init__(self, root_path: Path):
        super().__init__()
        self.root_path = root_path
        self.results: list[tuple[str, int, str]] = []
        self._use_rg = self._check_ripgrep()
        self._selected_idx: int = -1

    def _check_ripgrep(self) -> bool:
        """Check if ripgrep is available."""
        import shutil

        return shutil.which("rg") is not None

    def compose(self) -> ComposeResult:
        with Vertical(id="project-search-dialog"):
            with Horizontal(id="project-search-header"):
                yield Label("Find in Project")
                yield SearchInput(
                    id="project-search-input", placeholder="Enter search term..."
                )
                yield Button("Search", id="search-btn", variant="primary")
            yield VerticalScroll(id="project-search-results")
            with Horizontal(id="project-search-footer"):
                yield Static("Click Search or press Enter", id="result-count")
                yield Button("Open", id="open-file-btn")
                yield Button("Close", id="close-project-search")

    def on_mount(self) -> None:
        self.query_one("#project-search-input", SearchInput).focus()

    def on_search_input_enter_pressed(self, event: SearchInput.EnterPressed) -> None:
        """Handle Enter key in search input."""
        asyncio.create_task(self._do_search())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-project-search":
            self.dismiss("")
        elif event.button.id == "open-file-btn":
            self._open_selected_file()
        elif event.button.id == "search-btn":
            asyncio.create_task(self._do_search())

    def on_search_result_item_selected(self, event: SearchResultItem.Selected) -> None:
        """Handle double-click or Enter on search result."""
        self.dismiss(f"{event.filepath}:{event.line_num}")

    def action_do_search(self) -> None:
        """Action for Enter key - search or open file."""
        focused = self.app.focused
        if isinstance(focused, Input):
            asyncio.create_task(self._do_search())
        elif isinstance(focused, SearchResultItem):
            focused.post_message(
                SearchResultItem.Selected(focused.filepath, focused.line_num)
            )
        elif not isinstance(focused, Button):
            self._open_selected_file()

    def action_close_dialog(self) -> None:
        """Action for Escape key."""
        self.dismiss("")

    def _update_selection(self) -> None:
        """Update visual selection state."""
        results_container = self.query_one("#project-search-results")
        for item in results_container.query(SearchResultItem):
            if item.result_idx == self._selected_idx:
                item.add_class("-selected")
            else:
                item.remove_class("-selected")

    def _open_selected_file(self) -> None:
        """Open the currently selected file."""
        if 0 <= self._selected_idx < len(self.results):
            filepath, line_num, _ = self.results[self._selected_idx]
            self.dismiss(f"{filepath}:{line_num}")

    async def _do_search(self) -> None:
        search_text = self.query_one("#project-search-input", SearchInput).value
        if not search_text or len(search_text) < 2:
            self.query_one("#result-count", Static).update(
                "Enter at least 2 characters"
            )
            return

        results_container = self.query_one("#project-search-results", VerticalScroll)
        await results_container.remove_children()
        self.results = []
        self._selected_idx = -1

        self.query_one("#result-count", Static).update("Searching...")
        self.refresh()

        try:
            if self._use_rg:
                result = subprocess.run(
                    [
                        "rg",
                        "--line-number",
                        "--no-heading",
                        "--color=never",
                        "-m",
                        "50",
                        "-g",
                        "!node_modules",
                        "-g",
                        "!.git",
                        "-g",
                        "!__pycache__",
                        "-g",
                        "!*.min.*",
                        "-g",
                        "!.venv",
                        "--max-depth",
                        "10",
                        search_text,
                        str(self.root_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            else:
                result = subprocess.run(
                    [
                        "grep",
                        "-rn",
                        "-m",
                        "50",
                        "--include=*.py",
                        "--include=*.js",
                        "--include=*.ts",
                        "--include=*.tsx",
                        "--include=*.json",
                        "--include=*.md",
                        "--exclude-dir=node_modules",
                        "--exclude-dir=.git",
                        "--exclude-dir=__pycache__",
                        "--exclude-dir=.venv",
                        search_text,
                        str(self.root_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

            output = result.stdout.strip()
            if output:
                lines = output.split("\n")[:50]
                for idx, line in enumerate(lines):
                    parts = line.split(":", 2)
                    if len(parts) >= 3:
                        filepath, line_num, content = parts[0], parts[1], parts[2]
                        try:
                            rel_path = str(Path(filepath).relative_to(self.root_path))
                        except ValueError:
                            rel_path = filepath

                        if len(rel_path) > 40:
                            rel_path = "..." + rel_path[-37:]

                        self.results.append((filepath, int(line_num), content))

                        item = SearchResultItem(
                            filepath=filepath,
                            line_num=int(line_num),
                            content=content,
                            rel_path=rel_path,
                            root_path=self.root_path,
                            result_idx=len(self.results) - 1,
                            id=f"result-{len(self.results)-1}",
                        )
                        await results_container.mount(item)

                self.query_one("#result-count", Static).update(
                    f"{len(self.results)} matches (click to preview)"
                )
            else:
                self.query_one("#result-count", Static).update("No matches found")
        except subprocess.TimeoutExpired:
            self.query_one("#result-count", Static).update("Search timed out")
        except Exception as e:
            self.query_one("#result-count", Static).update(f"Error: {str(e)[:30]}")
