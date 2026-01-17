"""Main application for CLI-IDE."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Static,
    TabbedContent,
    TextArea,
)

from .config import Config
from .models import EditorPane, EditorState, OpenFile
from .utils import get_language, path_to_tab_id
from .widgets import (
    EditorPaneWidget,
    FileTree,
    ProjectSearchDialog,
    SaveConfirmDialog,
    SearchBar,
    SplitContainer,
    Terminal,
    TerminalInput,
)


class CliIdeApp(App):
    """Terminal-based IDE application with tabs and split view."""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 30;
        min-width: 15;
        max-width: 60;
        border-right: solid $primary;
    }

    #sidebar-header {
        height: 1;
        layout: horizontal;
        background: $surface-darken-1;
    }

    #sidebar-title {
        width: 1fr;
        padding: 0 1;
    }

    .resize-btn {
        width: 3;
        min-width: 3;
        height: 1;
        border: none;
        background: $surface-darken-1;
        color: $text-muted;
        padding: 0;
    }

    .resize-btn:hover {
        background: $primary;
        color: $text;
    }

    #file-tree {
        height: 1fr;
    }

    #main-area {
        width: 1fr;
    }

    #split-container {
        height: 1fr;
        border-bottom: solid $primary;
    }

    #split-container.horizontal {
        layout: horizontal;
    }

    #split-container.vertical {
        layout: vertical;
    }

    EditorPaneWidget {
        height: 1fr;
        width: 1fr;
    }

    #split-container.horizontal > EditorPaneWidget.left-pane {
        border-right: solid $primary;
    }

    #split-container.vertical > EditorPaneWidget.top-pane {
        border-bottom: solid $primary;
    }

    .pane-path-bar {
        height: 1;
        background: $primary;
        color: $text;
        padding: 0 2;
    }

    .pane-path-bar.inactive {
        background: $surface-darken-2;
    }

    TabbedContent {
        height: 1fr;
    }

    ContentTabs {
        height: 1;
        background: $surface-darken-1;
    }

    Tab {
        height: 1;
        padding: 0 2;
        background: $surface;
        color: $text-muted;
        min-width: 12;
    }

    Tab:hover {
        background: $boost;
    }

    Tab.-active {
        background: $surface-darken-2;
        color: $text;
        text-style: bold;
    }

    Underline {
        height: 0;
    }

    TabPane {
        height: 1fr;
        padding: 0;
    }

    /* Search Bar Styles */
    SearchBar {
        height: 3;
        background: $surface;
        display: none;
    }

    SearchBar.visible {
        display: block;
    }

    EditorPaneWidget {
        layout: vertical;
    }

    SearchBar #search-bar-content {
        width: 100%;
        height: 3;
        layout: horizontal;
    }

    SearchBar #search-input {
        width: 1fr;
        height: 3;
    }

    SearchBar .search-btn {
        width: 5;
        min-width: 5;
        height: 3;
    }

    SearchBar #search-status {
        width: 12;
        height: 3;
        content-align: center middle;
    }

    /* MultiSelect Status Styles */
    .multiselect-status {
        height: 1;
        background: $warning;
        color: $text;
        padding: 0 2;
        display: none;
    }

    .multiselect-status.visible {
        display: block;
    }

    #terminal-container {
        height: 14;
        min-height: 5;
        max-height: 30;
        background: $surface;
    }

    #terminal-header {
        height: 1;
        layout: horizontal;
        background: $surface-darken-1;
        dock: top;
    }

    #terminal-title {
        width: 1fr;
        padding: 0 1;
    }

    #terminal-output {
        height: 1fr;
        overflow-y: auto;
        padding: 0 1;
    }

    #terminal-input {
        height: 1;
        dock: bottom;
        padding: 0 1;
        background: $surface-darken-1;
    }

    #terminal-input:focus {
        background: $primary;
    }
    """

    BINDINGS = [
        # File operations
        Binding("ctrl+s", "save_file", "Save"),
        Binding("ctrl+q", "quit", "Quit"),
        # Focus
        Binding("ctrl+t", "focus_terminal", "Terminal", priority=True),
        Binding("ctrl+e", "focus_editor", "Editor", priority=True),
        Binding("ctrl+b", "toggle_sidebar", "Sidebar"),
        # Tab operations
        Binding("ctrl+w", "close_tab", "Close Tab", priority=True),
        Binding("alt+1", "goto_tab_1", "Tab 1", show=False),
        Binding("alt+2", "goto_tab_2", "Tab 2", show=False),
        Binding("alt+3", "goto_tab_3", "Tab 3", show=False),
        Binding("alt+4", "goto_tab_4", "Tab 4", show=False),
        Binding("alt+5", "goto_tab_5", "Tab 5", show=False),
        Binding("alt+6", "goto_tab_6", "Tab 6", show=False),
        Binding("alt+7", "goto_tab_7", "Tab 7", show=False),
        Binding("alt+8", "goto_tab_8", "Tab 8", show=False),
        Binding("alt+9", "goto_tab_9", "Tab 9", show=False),
        # Split operations - move file to split pane (creates split if needed)
        Binding("ctrl+shift+left", "move_file_left", "Move Left", priority=True),
        Binding("ctrl+shift+right", "move_file_right", "Move Right", priority=True),
        Binding("ctrl+shift+up", "move_file_up", "Move Up", priority=True),
        Binding("ctrl+shift+down", "move_file_down", "Move Down", priority=True),
        # Search operations
        Binding("ctrl+f", "find_in_file", "Find", priority=True),
        Binding("ctrl+g", "find_in_project", "Find All", priority=True),
        # Edit operations
        Binding("ctrl+i", "select_next_match", "Select Match", priority=True),
        Binding("ctrl+d", "delete_line", "Delete Line", priority=True),
        # Multi-select operations
        Binding("enter", "apply_multiselect", "Apply Multi", priority=True, show=False),
        Binding("escape", "cancel_multiselect", "Cancel Multi", priority=True, show=False),
    ]

    def __init__(self, path: str | None = None):
        super().__init__()
        self.root_path = Path(path) if path else Path.cwd()
        self.config = Config.load(self.root_path)
        self.editor_state = EditorState()
        self._terminal: Terminal | None = None
        self._last_search: str = ""
        self._last_search_pos: int = 0

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal():
            with Vertical(id="sidebar"):
                with Horizontal(id="sidebar-header"):
                    yield Static("Files", id="sidebar-title")
                    yield Button("-", id="sidebar-shrink", classes="resize-btn")
                    yield Button("+", id="sidebar-grow", classes="resize-btn")
                yield FileTree(self.root_path, id="file-tree")

            with Vertical(id="main-area"):
                yield SplitContainer()

                with Vertical(id="terminal-container"):
                    with Horizontal(id="terminal-header"):
                        yield Static("Terminal", id="terminal-title")
                        yield Button("-", id="terminal-shrink", classes="resize-btn")
                        yield Button("+", id="terminal-grow", classes="resize-btn")
                    self._terminal = Terminal(
                        working_dir=self.root_path, id="terminal-output"
                    )
                    yield self._terminal
                    yield TerminalInput(self._terminal, id="terminal-input")

        yield Footer()

    def on_mount(self) -> None:
        self.theme = "textual-light"
        self.title = "CLI-IDE"
        self.sub_title = str(self.root_path)
        self._update_active_pane_style()

        # Apply config
        sidebar = self.query_one("#sidebar")
        sidebar.styles.width = self.config.sidebar.width
        if not self.config.sidebar.visible:
            sidebar.display = False

        terminal = self.query_one("#terminal-container")
        terminal.styles.height = self.config.terminal.height

    def _update_active_pane_style(self) -> None:
        """Update visual style to show active pane via path bar color."""
        for pane in self.query(EditorPaneWidget):
            try:
                path_bar = pane.query_one(".pane-path-bar", Static)
                if pane.pane_id == self.editor_state.active_pane_id:
                    path_bar.remove_class("inactive")
                else:
                    path_bar.add_class("inactive")
            except Exception:
                pass

    def _resize_sidebar(self, delta: int) -> None:
        """Resize sidebar width by delta."""
        sidebar = self.query_one("#sidebar")
        current_width = sidebar.styles.width
        if current_width is not None:
            new_width = max(15, min(60, int(current_width.value) + delta))
            sidebar.styles.width = new_width

    def _resize_terminal(self, delta: int) -> None:
        """Resize terminal height by delta."""
        terminal = self.query_one("#terminal-container")
        current_height = terminal.styles.height
        if current_height is not None:
            new_height = max(5, min(30, int(current_height.value) + delta))
            terminal.styles.height = new_height

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle resize button clicks."""
        button_id = event.button.id
        if button_id == "sidebar-shrink":
            self._resize_sidebar(-5)
        elif button_id == "sidebar-grow":
            self._resize_sidebar(5)
        elif button_id == "terminal-shrink":
            self._resize_terminal(-3)
        elif button_id == "terminal-grow":
            self._resize_terminal(3)

    def on_editor_pane_widget_pane_focused(
        self, event: EditorPaneWidget.PaneFocused
    ) -> None:
        """Handle pane focus change."""
        self.editor_state.active_pane_id = event.pane_id
        self._update_active_pane_style()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Handle file selection from the tree."""
        self.open_file(event.path)

    def open_file(self, path: Path) -> None:
        """Open a file in the active pane."""
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            self.notify("Cannot open binary file", severity="error")
            return
        except Exception as e:
            self.notify(f"Error opening file: {e}", severity="error")
            return

        # Add to editor state
        pane = self.editor_state.active_pane
        if not pane:
            return

        language = get_language(path)
        open_file = OpenFile(
            path=path,
            content=content,
            original_content=content,
            language=language,
        )
        pane.add_file(open_file)

        # Open in UI
        pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)

        async def _open_file_async():
            try:
                await pane_widget.open_file(path, content, language)
            except Exception:
                self.notify(f"Error opening tab: {path.name}", severity="error")

        self.call_later(lambda: asyncio.create_task(_open_file_async()))

        self.notify(f"Opened: {path.name}")

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """Handle tab activation."""
        # Find which pane this belongs to
        tabs = event.tabbed_content
        pane_widget = tabs.parent
        if isinstance(pane_widget, EditorPaneWidget):
            # Update active file in state
            pane = self.editor_state.get_pane_by_id(pane_widget.pane_id)
            if pane:
                # Find path for this tab
                tab_id = event.pane.id
                for path_str, open_file in pane.open_files.items():
                    if path_to_tab_id(open_file.path) == tab_id:
                        pane.active_file = path_str
                        pane_widget._update_path_bar(
                            open_file.path, open_file.is_modified
                        )
                        break

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Track file modifications."""
        # Find which file was modified
        editor = event.text_area
        editor_id = editor.id
        if not editor_id or not editor_id.startswith("editor-"):
            return

        tab_id = editor_id.replace("editor-", "")

        # Find the file in state
        for pane in self.editor_state.panes:
            for path_str, open_file in pane.open_files.items():
                if path_to_tab_id(open_file.path) == tab_id:
                    open_file.content = editor.text

                    # Update UI
                    try:
                        pane_widget = self.query_one(
                            f"#pane-{pane.id}", EditorPaneWidget
                        )
                        pane_widget.update_tab_label(
                            open_file.path, open_file.is_modified
                        )
                        if pane.active_file == path_str:
                            pane_widget._update_path_bar(
                                open_file.path, open_file.is_modified
                            )
                    except Exception:
                        pass
                    return

    def action_save_file(self) -> None:
        """Save the current file."""
        open_file = self.editor_state.active_file
        if not open_file:
            self.notify("No file open", severity="warning")
            return

        try:
            open_file.path.write_text(open_file.content, encoding="utf-8")
            open_file.original_content = open_file.content

            # Update UI
            pane = self.editor_state.active_pane
            if pane:
                try:
                    pane_widget = self.query_one(
                        f"#pane-{pane.id}", EditorPaneWidget
                    )
                    pane_widget.update_tab_label(open_file.path, False)
                    pane_widget._update_path_bar(open_file.path, False)
                except Exception:
                    pass

            self.notify(f"Saved: {open_file.path.name}")
        except Exception as e:
            self.notify(f"Error saving: {e}", severity="error")

    async def action_close_tab(self) -> None:
        """Close the current tab. If no tabs left and split, close split."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        # If no active file, try to close split if in split mode
        if not pane.active_file:
            if self.editor_state.split_orientation != "none":
                await self._close_current_split()
            return

        open_file = pane.open_files.get(pane.active_file)
        if not open_file:
            return

        # Check if modified
        if open_file.is_modified:
            result = await self.push_screen_wait(
                SaveConfirmDialog(open_file.path.name)
            )
            if result == "cancel":
                return
            elif result == "save":
                self.action_save_file()

        # Close the tab
        tab_id = path_to_tab_id(open_file.path)
        next_file = pane.remove_file(open_file.path)

        try:
            pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)
            await pane_widget.close_tab(tab_id)

            # Activate next tab or close split if no tabs left
            if next_file:
                pane.active_file = next_file
                next_open_file = pane.open_files.get(next_file)
                if next_open_file:
                    next_tab_id = path_to_tab_id(next_open_file.path)
                    tabs = pane_widget.query_one(
                        f"#tabs-{pane.id}", TabbedContent
                    )
                    tabs.active = next_tab_id
            elif self.editor_state.split_orientation != "none":
                # No tabs left, close the split
                await self._close_current_split()
        except Exception:
            pass

    async def _close_current_split(self) -> None:
        """Close the current split pane without checking for unsaved files."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        split_container = self.query_one(SplitContainer)
        other_pane_id = split_container.get_other_pane_id(pane.id)

        if await split_container.close_split(pane.id):
            self.editor_state.panes.remove(pane)
            self.editor_state.split_orientation = "none"
            if other_pane_id:
                self.editor_state.active_pane_id = other_pane_id
            self._update_active_pane_style()

    def action_next_tab(self) -> None:
        """Switch to next tab."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        next_file = pane.get_next_file()
        if next_file:
            pane.active_file = next_file
            open_file = pane.open_files.get(next_file)
            if open_file:
                tab_id = path_to_tab_id(open_file.path)
                try:
                    pane_widget = self.query_one(
                        f"#pane-{pane.id}", EditorPaneWidget
                    )
                    tabs = pane_widget.query_one(
                        f"#tabs-{pane.id}", TabbedContent
                    )
                    tabs.active = tab_id
                except Exception:
                    pass

    def action_prev_tab(self) -> None:
        """Switch to previous tab."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        prev_file = pane.get_prev_file()
        if prev_file:
            pane.active_file = prev_file
            open_file = pane.open_files.get(prev_file)
            if open_file:
                tab_id = path_to_tab_id(open_file.path)
                try:
                    pane_widget = self.query_one(
                        f"#pane-{pane.id}", EditorPaneWidget
                    )
                    tabs = pane_widget.query_one(
                        f"#tabs-{pane.id}", TabbedContent
                    )
                    tabs.active = tab_id
                except Exception:
                    pass

    def _goto_tab(self, index: int) -> None:
        """Go to tab at specific index."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        file_path = pane.get_file_at_index(index)
        if file_path:
            pane.active_file = file_path
            open_file = pane.open_files.get(file_path)
            if open_file:
                tab_id = path_to_tab_id(open_file.path)
                try:
                    pane_widget = self.query_one(
                        f"#pane-{pane.id}", EditorPaneWidget
                    )
                    tabs = pane_widget.query_one(
                        f"#tabs-{pane.id}", TabbedContent
                    )
                    tabs.active = tab_id
                except Exception:
                    pass

    def action_goto_tab_1(self) -> None:
        self._goto_tab(0)

    def action_goto_tab_2(self) -> None:
        self._goto_tab(1)

    def action_goto_tab_3(self) -> None:
        self._goto_tab(2)

    def action_goto_tab_4(self) -> None:
        self._goto_tab(3)

    def action_goto_tab_5(self) -> None:
        self._goto_tab(4)

    def action_goto_tab_6(self) -> None:
        self._goto_tab(5)

    def action_goto_tab_7(self) -> None:
        self._goto_tab(6)

    def action_goto_tab_8(self) -> None:
        self._goto_tab(7)

    def action_goto_tab_9(self) -> None:
        # Alt+9 goes to last tab
        pane = self.editor_state.active_pane
        if pane and pane.tab_order:
            self._goto_tab(len(pane.tab_order) - 1)

    async def _move_file_to_split(self, direction: str) -> None:
        """Move current file to a split pane in the given direction.

        Args:
            direction: "left", "right", "up", or "down"
        """
        pane = self.editor_state.active_pane
        if not pane or not pane.active_file:
            self.notify("No file to move", severity="warning")
            return

        open_file = pane.open_files.get(pane.active_file)
        if not open_file:
            return

        split_container = self.query_one(SplitContainer)
        current_orientation = self.editor_state.split_orientation

        # Determine required orientation based on direction
        is_horizontal_move = direction in ("left", "right")
        required_orientation = "horizontal" if is_horizontal_move else "vertical"

        # Check orientation conflict
        if current_orientation != "none" and current_orientation != required_orientation:
            self.notify(
                f"Cannot move {direction}: already have {current_orientation} split",
                severity="warning",
            )
            return

        # If no split exists, create one
        if current_orientation == "none":
            if is_horizontal_move:
                new_pane_id = await split_container.split_horizontal()
            else:
                new_pane_id = await split_container.split_vertical()

            if new_pane_id:
                new_pane = EditorPane(id=new_pane_id)
                self.editor_state.panes.append(new_pane)
                self.editor_state.split_orientation = required_orientation

        # Get pane IDs after potential split creation
        pane_ids = split_container.get_pane_ids()
        if len(pane_ids) < 2:
            return

        # Determine target pane based on direction
        # pane_ids[0] is left/top, pane_ids[1] is right/bottom
        current_is_first = pane.id == pane_ids[0]

        if direction in ("left", "up"):
            # Move to first pane (left/top)
            if current_is_first:
                # Already in first pane, nothing to do
                return
            target_pane_id = pane_ids[0]
        else:
            # Move to second pane (right/bottom)
            if not current_is_first:
                # Already in second pane, nothing to do
                return
            target_pane_id = pane_ids[1]

        target_pane = self.editor_state.get_pane_by_id(target_pane_id)
        if not target_pane:
            return

        # Close tab in current pane
        tab_id = path_to_tab_id(open_file.path)
        try:
            pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)
            await pane_widget.close_tab(tab_id)
        except Exception:
            pass

        # Remove from current pane state
        next_file = pane.remove_file(open_file.path)

        # Add to target pane state
        target_pane.add_file(open_file)

        # Open in target pane UI
        try:
            target_pane_widget = self.query_one(
                f"#pane-{target_pane.id}", EditorPaneWidget
            )
            await target_pane_widget.open_file(
                open_file.path, open_file.content, open_file.language
            )
        except Exception:
            pass

        # Switch focus to target pane
        self.editor_state.active_pane_id = target_pane_id
        self._update_active_pane_style()
        self._focus_active_editor()

    async def action_move_file_left(self) -> None:
        """Move current file to left pane (creates horizontal split if needed)."""
        await self._move_file_to_split("left")

    async def action_move_file_right(self) -> None:
        """Move current file to right pane (creates horizontal split if needed)."""
        await self._move_file_to_split("right")

    async def action_move_file_up(self) -> None:
        """Move current file to top pane (creates vertical split if needed)."""
        await self._move_file_to_split("up")

    async def action_move_file_down(self) -> None:
        """Move current file to bottom pane (creates vertical split if needed)."""
        await self._move_file_to_split("down")

    def _focus_active_editor(self) -> None:
        """Focus the editor in the active pane."""
        pane = self.editor_state.active_pane
        if pane:
            try:
                pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)
                editor = pane_widget.get_active_editor()
                if editor:
                    editor.focus()
            except Exception:
                pass

    def action_focus_terminal(self) -> None:
        """Focus the terminal input."""
        self.query_one("#terminal-input", TerminalInput).focus()

    def action_focus_editor(self) -> None:
        """Focus the active editor."""
        self._focus_active_editor()

    def action_toggle_sidebar(self) -> None:
        """Toggle sidebar visibility."""
        sidebar = self.query_one("#sidebar", Container)
        sidebar.display = not sidebar.display

    def action_find_in_file(self) -> None:
        """Show inline search bar."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        initial_text = ""
        try:
            pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)
            editor = pane_widget.get_active_editor()
            if editor and editor.selected_text:
                initial_text = editor.selected_text
            elif self._last_search:
                initial_text = self._last_search
            pane_widget.show_search_bar(initial_text)
        except Exception:
            pass

    def on_search_bar_search_submitted(self, event: SearchBar.SearchSubmitted) -> None:
        """Handle search from inline search bar."""
        self._last_search = event.query
        self._find_text(event.query, reverse=(event.direction == "prev"))

    def on_search_bar_search_closed(self, event: SearchBar.SearchClosed) -> None:
        """Handle search bar close."""
        pane = self.editor_state.active_pane
        if pane:
            try:
                pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)
                pane_widget.hide_search_bar()
            except Exception:
                pass

    def _find_text(self, search_text: str, reverse: bool = False) -> None:
        """Find text in current editor."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        try:
            pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)
            editor = pane_widget.get_active_editor()
            if not editor:
                return

            content = editor.text
            cursor_loc = editor.cursor_location

            # Count total matches
            total_matches = content.count(search_text)

            # Convert cursor location to position
            lines = content.split("\n")
            current_pos = (
                sum(len(lines[i]) + 1 for i in range(cursor_loc[0])) + cursor_loc[1]
            )

            if reverse:
                pos = content.rfind(search_text, 0, current_pos)
                if pos == -1:
                    pos = content.rfind(search_text)
            else:
                pos = content.find(search_text, current_pos + 1)
                if pos == -1:
                    pos = content.find(search_text)

            if pos != -1:
                text_before = content[:pos]
                row = text_before.count("\n")
                last_newline = text_before.rfind("\n")
                col = pos - last_newline - 1 if last_newline != -1 else pos

                editor.cursor_location = (row, col)
                end_col = col + len(search_text)
                editor.selection = ((row, col), (row, end_col))
                self._last_search_pos = pos

                # Calculate current match index
                current_match = content[: pos + 1].count(search_text)

                # Update search bar status
                try:
                    search_bar = pane_widget.query_one(
                        f"#search-bar-{pane.id}", SearchBar
                    )
                    search_bar.set_status(f"{current_match}/{total_matches}")
                except Exception:
                    pass
            else:
                try:
                    search_bar = pane_widget.query_one(
                        f"#search-bar-{pane.id}", SearchBar
                    )
                    search_bar.set_status("No results")
                except Exception:
                    pass
        except Exception:
            pass

    def action_find_in_project(self) -> None:
        """Open project search dialog."""

        def handle_result(result: str) -> None:
            if result:
                # Parse result: "filepath:line_number"
                try:
                    parts = result.rsplit(":", 1)
                    if len(parts) == 2:
                        filepath, line_num = parts[0], int(parts[1])
                        path = Path(filepath)
                        if path.exists():
                            self.open_file(path)
                            # Move cursor to line after file opens
                            self.call_later(lambda: self._goto_line(line_num))
                except Exception:
                    pass

        self.push_screen(ProjectSearchDialog(self.root_path), handle_result)

    def _goto_line(self, line_num: int) -> None:
        """Go to a specific line number in the active editor."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        try:
            pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)
            editor = pane_widget.get_active_editor()
            if editor:
                # Line numbers are 1-indexed in grep output, 0-indexed in TextArea
                row = max(0, line_num - 1)
                editor.cursor_location = (row, 0)
                editor.focus()
        except Exception:
            pass

    def action_select_next_match(self) -> None:
        """Add next occurrence of selected text to multi-select (ctrl+i)."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        try:
            pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)
            editor = pane_widget.get_active_editor()
            if not editor:
                return

            ms = pane_widget.multi_select
            selected = editor.selected_text

            if not selected:
                # Select current word first
                self._select_current_word(editor)
                selected = editor.selected_text
                if not selected:
                    return

            # If starting fresh or different text selected
            if not ms.active or ms.target_text != selected:
                ms.reset()
                ms.target_text = selected
                ms.active = True
                # Get current selection position
                sel = editor.selection
                if sel:
                    ms.original_selection = sel[0]  # Start of selection
                    ms.add_position(sel[0][0], sel[0][1])
                pane_widget.update_multiselect_status()

            # Find next occurrence after the last highlighted position
            content = editor.text

            # Determine search start position
            if ms.highlighted_positions:
                last_pos = ms.highlighted_positions[-1]
                # Convert row, col to string position
                lines = content.split("\n")
                search_start = (
                    sum(len(lines[i]) + 1 for i in range(last_pos[0]))
                    + last_pos[1]
                    + len(ms.target_text)
                )
            else:
                search_start = 0

            # Find next occurrence
            pos = content.find(ms.target_text, search_start)
            if pos == -1:
                # Wrap around to beginning
                pos = content.find(ms.target_text, 0)

            if pos != -1:
                # Convert position to row, col
                text_before = content[:pos]
                row = text_before.count("\n")
                last_newline = text_before.rfind("\n")
                col = pos - last_newline - 1 if last_newline != -1 else pos

                # Check if this position is already highlighted
                if (row, col) not in ms.highlighted_positions:
                    ms.add_position(row, col)
                    pane_widget.update_multiselect_status()
                    self.notify(f"Selected {ms.count} matches")
                else:
                    self.notify("All occurrences selected")
            else:
                self.notify("No more matches")
        except Exception:
            pass

    def _apply_multiselect_change(
        self, pane_widget: EditorPaneWidget, new_text: str
    ) -> None:
        """Apply text change to all multi-selected positions (supports undo)."""
        ms = pane_widget.multi_select
        if not ms.active or ms.count <= 1:
            return

        editor = pane_widget.get_active_editor()
        if not editor:
            return

        target_len = len(ms.target_text)

        # Sort positions in reverse order (bottom-right to top-left) to maintain positions
        sorted_positions = sorted(ms.highlighted_positions, reverse=True)

        for row, col in sorted_positions:
            # Skip the primary position (already changed by user)
            if (row, col) == ms.original_selection:
                continue

            # Use delete and insert for undo support
            start_pos = (row, col)
            end_pos = (row, col + target_len)

            # Delete old text
            editor.delete(start_pos, end_pos)
            # Insert new text
            editor.insert(new_text, start_pos)

        # Clear multi-select after applying
        pane_widget.clear_multiselect()

    def action_apply_multiselect(self) -> None:
        """Apply multi-select changes (Enter key)."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        try:
            pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)
            ms = pane_widget.multi_select

            if not ms.active or ms.count <= 1:
                # Not in multi-select mode, let Enter work normally
                return

            editor = pane_widget.get_active_editor()
            if not editor:
                return

            # Get the new text from original selection position
            new_text = editor.selected_text
            if not new_text:
                # Get text at cursor position (user may have typed something)
                # We need to find what replaced the original selection
                content = editor.text
                lines = content.split("\n")
                cursor = editor.cursor_location

                # The user's cursor should be at the end of what they typed
                # Find the text between original selection start and cursor
                orig_row, orig_col = ms.original_selection

                if cursor[0] == orig_row:
                    # Same line - extract text between original col and cursor
                    line = lines[orig_row]
                    new_text = line[orig_col : cursor[1]]
                else:
                    # Different line - just use what's selected or empty
                    new_text = ""

            if new_text and new_text != ms.target_text:
                self._apply_multiselect_change(pane_widget, new_text)
                self.notify(f"Replaced {ms.count} occurrences")
            else:
                pane_widget.clear_multiselect()
        except Exception:
            pass

    def action_cancel_multiselect(self) -> None:
        """Cancel multi-select mode (Escape key)."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        try:
            pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)
            ms = pane_widget.multi_select

            if ms.active:
                pane_widget.clear_multiselect()
                self.notify("Multi-select cancelled")
        except Exception:
            pass

    def _select_current_word(self, editor: TextArea) -> None:
        """Select the word under cursor."""
        content = editor.text
        cursor_loc = editor.cursor_location
        lines = content.split("\n")

        if cursor_loc[0] >= len(lines):
            return

        line = lines[cursor_loc[0]]
        col = cursor_loc[1]

        if col >= len(line):
            return

        # Find word boundaries
        start = col
        end = col

        while start > 0 and (line[start - 1].isalnum() or line[start - 1] == "_"):
            start -= 1

        while end < len(line) and (line[end].isalnum() or line[end] == "_"):
            end += 1

        if start < end:
            editor.selection = ((cursor_loc[0], start), (cursor_loc[0], end))

    def action_delete_line(self) -> None:
        """Delete the current line (supports undo)."""
        pane = self.editor_state.active_pane
        if not pane:
            return

        try:
            pane_widget = self.query_one(f"#pane-{pane.id}", EditorPaneWidget)
            editor = pane_widget.get_active_editor()
            if not editor:
                return

            cursor_loc = editor.cursor_location
            row = cursor_loc[0]
            lines = editor.text.split("\n")

            if row >= len(lines):
                return

            # Calculate start and end positions for deletion
            line_start = (row, 0)
            if row < len(lines) - 1:
                # Not the last line: delete up to start of next line
                line_end = (row + 1, 0)
            else:
                # Last line: delete to end of line
                line_end = (row, len(lines[row]))
                # If not the first line, include the previous newline
                if row > 0:
                    line_start = (row - 1, len(lines[row - 1]))

            # Use delete method (this is undoable)
            editor.delete(line_start, line_end)
        except Exception:
            pass


def main():
    """Entry point."""
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else None
    app = CliIdeApp(path)
    app.run()


if __name__ == "__main__":
    main()
