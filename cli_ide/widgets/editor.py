"""Editor widgets for CLI-IDE."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.message import Message
from textual.widgets import Static, TabbedContent, TabPane, TextArea

from ..models import MultiSelectState
from ..themes import LIGHT_THEME
from ..utils import path_to_tab_id
from .search import SearchBar


class CodeEditor(TextArea):
    """Custom TextArea that doesn't capture app-level keybindings."""

    # Keys that should be passed to the app instead of handled by the editor
    PASSTHROUGH_KEYS = {
        "super+left", "super+right", "super+up", "super+down",
        "ctrl+w", "ctrl+f", "ctrl+g", "ctrl+d",
    }

    def _on_key(self, event: events.Key) -> None:
        """Handle key events, passing some through to the app."""
        if event.key in self.PASSTHROUGH_KEYS:
            return
        super()._on_key(event)


class EditorPaneWidget(Container):
    """Single editor pane containing tabbed editors.

    A self-contained editor widget with tabs, search bar, and multi-select support.
    Can be used independently or as part of a split view.

    Args:
        pane_id: Unique identifier for this pane. Defaults to a random UUID.

    Example:
        ```python
        from textual.app import App, ComposeResult
        from cli_ide.widgets import EditorPaneWidget

        class MyApp(App):
            def compose(self) -> ComposeResult:
                yield EditorPaneWidget()

            async def on_mount(self) -> None:
                pane = self.query_one(EditorPaneWidget)
                await pane.open_file(Path("example.py"), "print('hello')", "python")
        ```
    """

    class PaneFocused(Message):
        """Message sent when pane receives focus."""

        def __init__(self, pane_id: str):
            super().__init__()
            self.pane_id = pane_id

    can_focus = True  # Allow clicking on empty pane to focus it

    def __init__(self, pane_id: str | None = None, **kwargs):
        pane_id = pane_id or str(uuid.uuid4())[:8]
        super().__init__(id=f"pane-{pane_id}", **kwargs)
        self.pane_id = pane_id
        self._search_matches: list[tuple[int, int, int]] = []  # (row, col, length)
        self._current_match_idx: int = -1
        self.multi_select = MultiSelectState()

    def compose(self) -> ComposeResult:
        yield Static("No file open", classes="pane-path-bar")
        yield TabbedContent(id=f"tabs-{self.pane_id}")
        yield SearchBar(id=f"search-bar-{self.pane_id}")
        yield Static("", id=f"multiselect-status-{self.pane_id}", classes="multiselect-status")

    def show_search_bar(self, initial_text: str = "") -> None:
        """Show the inline search bar."""
        search_bar = self.query_one(f"#search-bar-{self.pane_id}", SearchBar)
        search_bar.add_class("visible")
        if initial_text:
            search_bar.set_query(initial_text)
        else:
            search_bar.focus_input()

    def hide_search_bar(self) -> None:
        """Hide the inline search bar."""
        search_bar = self.query_one(f"#search-bar-{self.pane_id}", SearchBar)
        search_bar.remove_class("visible")
        self._search_matches = []
        self._current_match_idx = -1
        # Focus back to editor
        editor = self.get_active_editor()
        if editor:
            editor.focus()

    def update_multiselect_status(self) -> None:
        """Update the multi-select status display and highlights."""
        status = self.query_one(f"#multiselect-status-{self.pane_id}", Static)
        if self.multi_select.active and self.multi_select.count > 0:
            status.update(f"Multi-select: {self.multi_select.count} matches")
            status.add_class("visible")
            # Apply highlights to editor
            self._apply_multiselect_highlights()
        else:
            status.update("")
            status.remove_class("visible")
            # Clear highlights
            self._clear_multiselect_highlights()

    def _apply_multiselect_highlights(self) -> None:
        """Apply highlight styling to multi-selected positions."""
        editor = self.get_active_editor()
        if not editor or not self.multi_select.active:
            return

        ms = self.multi_select
        target_len = len(ms.target_text)

        # Use TextArea's internal _highlights dict
        # Format: _highlights[line_number] = [(start_col, end_col, highlight_name), ...]
        for row, col in ms.highlighted_positions:
            if row not in editor._highlights:
                editor._highlights[row] = []
            # Add multiselect highlight
            highlight_entry = (col, col + target_len, "multiselect")
            if highlight_entry not in editor._highlights[row]:
                editor._highlights[row].append(highlight_entry)

        editor.refresh()

    def _clear_multiselect_highlights(self) -> None:
        """Clear multi-select highlights from editor."""
        editor = self.get_active_editor()
        if not editor:
            return

        # Remove multiselect highlights from all lines
        for line_num in list(editor._highlights.keys()):
            editor._highlights[line_num] = [
                h
                for h in editor._highlights[line_num]
                if len(h) < 3 or h[2] != "multiselect"
            ]
            # Clean up empty entries
            if not editor._highlights[line_num]:
                del editor._highlights[line_num]

        editor.refresh()

    def clear_multiselect(self) -> None:
        """Clear multi-select mode."""
        self._clear_multiselect_highlights()
        self.multi_select.reset()
        self.update_multiselect_status()

    def on_focus(self, event: events.Focus) -> None:
        self.post_message(self.PaneFocused(self.pane_id))

    def on_click(self, event: events.Click) -> None:
        self.post_message(self.PaneFocused(self.pane_id))

    async def open_file(
        self, path: Path, content: str, language: Optional[str] = None
    ) -> None:
        """Open a file in a new tab or switch to existing tab."""
        tabs = self.query_one(f"#tabs-{self.pane_id}", TabbedContent)
        tab_id = path_to_tab_id(path)

        # Check if already open
        existing_tabs = tabs.query(TabPane)
        for tab in existing_tabs:
            if tab.id == tab_id:
                tabs.active = tab_id
                self._update_path_bar(path)
                return

        # Create new tab with editor
        editor = CodeEditor(
            content,
            id=f"editor-{tab_id}",
            show_line_numbers=True,
            tab_behavior="indent",
        )

        # Register theme for this editor
        editor.register_theme(LIGHT_THEME)
        editor.theme = "light-ide"

        if language:
            try:
                editor.language = language
            except Exception:
                pass

        pane = TabPane(path.name, editor, id=tab_id)
        await tabs.add_pane(pane)
        tabs.active = tab_id
        self._update_path_bar(path)

    def _update_path_bar(self, path: Path, modified: bool = False) -> None:
        path_bar = self.query_one(".pane-path-bar", Static)
        display = f"* {path}" if modified else str(path)
        path_bar.update(display)

    def update_tab_label(self, path: Path, modified: bool) -> None:
        """Update tab label to show modified state."""
        tabs = self.query_one(f"#tabs-{self.pane_id}", TabbedContent)
        tab_id = path_to_tab_id(path)
        name = path.name
        display = f"* {name}" if modified else name

        # Find and update the tab
        try:
            # TabbedContent uses ContentTabs internally
            content_tabs = tabs.query_one("ContentTabs")
            for tab in content_tabs.query("Tab"):
                if tab.id and tab.id.endswith(tab_id):
                    tab.label = display
                    break
        except Exception:
            pass

    async def close_tab(self, tab_id: str) -> None:
        """Close a tab by ID."""
        tabs = self.query_one(f"#tabs-{self.pane_id}", TabbedContent)
        await tabs.remove_pane(tab_id)

        # Update path bar
        remaining = list(tabs.query(TabPane))
        if not remaining:
            path_bar = self.query_one(".pane-path-bar", Static)
            path_bar.update("No file open")

    def get_active_tab_id(self) -> Optional[str]:
        """Get currently active tab ID."""
        tabs = self.query_one(f"#tabs-{self.pane_id}", TabbedContent)
        return tabs.active if tabs.active else None

    def get_active_editor(self) -> Optional[CodeEditor]:
        """Get currently active editor."""
        tabs = self.query_one(f"#tabs-{self.pane_id}", TabbedContent)
        active_pane = tabs.active_pane
        if active_pane:
            try:
                return active_pane.query_one(CodeEditor)
            except Exception:
                return None
        return None

    def get_tab_count(self) -> int:
        """Get number of open tabs."""
        tabs = self.query_one(f"#tabs-{self.pane_id}", TabbedContent)
        return len(list(tabs.query(TabPane)))


class SplitContainer(Container):
    """Container that manages split editor panes."""

    DEFAULT_PANE_ID = "main"

    def __init__(self, **kwargs):
        super().__init__(id="split-container", **kwargs)
        self.orientation: str = "none"

    def compose(self) -> ComposeResult:
        yield EditorPaneWidget(pane_id=self.DEFAULT_PANE_ID)

    async def split_horizontal(self) -> Optional[str]:
        """Split horizontally (left/right). Returns new pane ID."""
        if self.orientation != "none":
            return None

        self.orientation = "horizontal"
        # Mark first pane as left
        first_pane = self.query_one(EditorPaneWidget)
        first_pane.add_class("left-pane")

        new_pane_id = str(uuid.uuid4())[:8]
        new_pane = EditorPaneWidget(pane_id=new_pane_id)
        await self.mount(new_pane)
        self.add_class("horizontal")
        return new_pane_id

    async def split_vertical(self) -> Optional[str]:
        """Split vertically (top/bottom). Returns new pane ID."""
        if self.orientation != "none":
            return None

        self.orientation = "vertical"
        # Mark first pane as top
        first_pane = self.query_one(EditorPaneWidget)
        first_pane.add_class("top-pane")

        new_pane_id = str(uuid.uuid4())[:8]
        new_pane = EditorPaneWidget(pane_id=new_pane_id)
        await self.mount(new_pane)
        self.add_class("vertical")
        return new_pane_id

    async def close_split(self, pane_id: str) -> bool:
        """Close a split pane. Returns True if closed."""
        panes = list(self.query(EditorPaneWidget))
        if len(panes) <= 1:
            return False

        try:
            pane = self.query_one(f"#pane-{pane_id}", EditorPaneWidget)
            await pane.remove()
            self.orientation = "none"
            self.remove_class("horizontal")
            self.remove_class("vertical")
            # Remove position classes from remaining pane
            remaining = self.query_one(EditorPaneWidget)
            remaining.remove_class("left-pane")
            remaining.remove_class("top-pane")
            return True
        except Exception:
            return False

    def get_pane_ids(self) -> list[str]:
        """Get all pane IDs."""
        return [pane.pane_id for pane in self.query(EditorPaneWidget)]

    def get_other_pane_id(self, current_id: str) -> Optional[str]:
        """Get the other pane ID in a split."""
        pane_ids = self.get_pane_ids()
        for pid in pane_ids:
            if pid != current_id:
                return pid
        return None
