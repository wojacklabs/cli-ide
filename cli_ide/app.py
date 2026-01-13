"""Main application for CLI-IDE."""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import os
import pty
import struct
import termios
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pyte
from rich.style import Style
from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)
from textual.widgets.text_area import TextAreaTheme

# Language mapping for syntax highlighting
LANG_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "javascript",
    ".tsx": "javascript",
    ".jsx": "javascript",
    ".json": "json",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".module.css": "css",
    ".scss": "css",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".rs": "rust",
    ".go": "go",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".sql": "sql",
    ".java": "java",
    ".xml": "xml",
}

# Custom light theme for syntax highlighting (matching textual-light)
LIGHT_THEME = TextAreaTheme(
    name="light-ide",
    # Based on textual-light app theme colors:
    # Primary: #004578, Secondary: #0178D4, Accent: #ffa62b
    # Background: #E0E0E0, Surface: #D8D8D8, Panel: #D0D0D0
    # Error: #ba3c5b, Success: #4EBF71, Warning: #ffa62b
    base_style=Style(color="#1a1a1a", bgcolor="#E0E0E0"),
    gutter_style=Style(color="#666666", bgcolor="#D8D8D8"),
    cursor_style=Style(color="#ffffff", bgcolor="#004578"),
    cursor_line_style=Style(bgcolor="#D0D0D0"),
    cursor_line_gutter_style=Style(color="#1a1a1a", bgcolor="#D0D0D0"),
    bracket_matching_style=Style(bgcolor="#ffa62b", bold=True),
    selection_style=Style(bgcolor="#a8c8e8"),
    syntax_styles={
        # Text formatting
        "bold": Style(bold=True),
        "italic": Style(italic=True),
        "strikethrough": Style(strike=True),
        # Keywords - Primary color
        "keyword": Style(color="#004578", bold=True),
        "keyword.function": Style(color="#004578", bold=True),
        "keyword.return": Style(color="#004578", bold=True),
        "keyword.operator": Style(color="#004578"),
        "conditional": Style(color="#004578", bold=True),
        "repeat": Style(color="#004578", bold=True),
        "exception": Style(color="#ba3c5b", bold=True),
        "include": Style(color="#004578", bold=True),
        # Functions and methods - Secondary color
        "function": Style(color="#0178D4"),
        "function.call": Style(color="#0178D4"),
        "method": Style(color="#0178D4"),
        "method.call": Style(color="#0178D4"),
        # Classes and types
        "class": Style(color="#0178D4", bold=True),
        "type": Style(color="#0178D4"),
        "type.builtin": Style(color="#0178D4"),
        "type.class": Style(color="#0178D4", bold=True),
        # Strings - Success color (green)
        "string": Style(color="#4EBF71"),
        "string.documentation": Style(color="#4EBF71", italic=True),
        "inline_code": Style(color="#4EBF71"),
        # Numbers and constants - Accent color (orange)
        "number": Style(color="#b35900"),
        "float": Style(color="#b35900"),
        "boolean": Style(color="#004578", italic=True),
        "constant.builtin": Style(color="#b35900"),
        # Comments - Muted gray
        "comment": Style(color="#6a737d", italic=True),
        # Operators and punctuation
        "operator": Style(color="#ba3c5b"),
        "punctuation.bracket": Style(color="#1a1a1a"),
        "punctuation.delimiter": Style(color="#1a1a1a"),
        "punctuation.special": Style(color="#ba3c5b"),
        # Variables and parameters
        "variable": Style(color="#1a1a1a"),
        "variable.parameter": Style(color="#b35900"),
        "parameter": Style(color="#b35900"),
        # Markdown
        "heading": Style(color="#004578", bold=True),
        "heading.marker": Style(color="#666666"),
        "list.marker": Style(color="#666666"),
        "link.label": Style(color="#0178D4"),
        "link.uri": Style(color="#0178D4", underline=True),
        # Tags (HTML/XML) - Secondary color
        "tag": Style(color="#0178D4"),
        # JSON
        "json.label": Style(color="#004578", bold=True),
        # YAML
        "yaml.field": Style(color="#004578", bold=True),
        # TOML
        "toml.type": Style(color="#0178D4"),
        # CSS
        "css.property": Style(color="#004578"),
        # Custom multi-select highlight
        "multiselect": Style(bgcolor="#ffa62b", color="#000000"),
    },
)

# ANSI color mapping for pyte
PYTE_COLORS = {
    "black": "#24292e",
    "red": "#cf222e",
    "green": "#116329",
    "brown": "#953800",
    "blue": "#0550ae",
    "magenta": "#8250df",
    "cyan": "#0969da",
    "white": "#6e7781",
    "default": "#24292e",
}

PYTE_BRIGHT_COLORS = {
    "black": "#57606a",
    "red": "#ff8182",
    "green": "#4ac26b",
    "brown": "#d4a72c",
    "blue": "#54aeff",
    "magenta": "#c297ff",
    "cyan": "#76e3ea",
    "white": "#ffffff",
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class OpenFile:
    """Represents an open file in the editor."""

    path: Path
    content: str
    original_content: str
    language: Optional[str] = None

    @property
    def is_modified(self) -> bool:
        return self.content != self.original_content

    @property
    def display_name(self) -> str:
        name = self.path.name
        return f"* {name}" if self.is_modified else name


@dataclass
class EditorPane:
    """Represents a single editor pane with tabs."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    open_files: dict[str, OpenFile] = field(default_factory=dict)
    active_file: Optional[str] = None
    tab_order: list[str] = field(default_factory=list)

    def add_file(self, open_file: OpenFile) -> None:
        path_str = str(open_file.path)
        if path_str not in self.open_files:
            self.open_files[path_str] = open_file
            self.tab_order.append(path_str)
        self.active_file = path_str

    def remove_file(self, path: Path) -> Optional[str]:
        """Remove file and return next file to activate."""
        path_str = str(path)
        if path_str in self.open_files:
            del self.open_files[path_str]
            idx = self.tab_order.index(path_str)
            self.tab_order.remove(path_str)

            if self.active_file == path_str:
                if self.tab_order:
                    new_idx = min(idx, len(self.tab_order) - 1)
                    return self.tab_order[new_idx]
                return None
        return self.active_file

    def get_next_file(self) -> Optional[str]:
        """Get next file in tab order."""
        if not self.tab_order or not self.active_file:
            return None
        idx = self.tab_order.index(self.active_file)
        next_idx = (idx + 1) % len(self.tab_order)
        return self.tab_order[next_idx]

    def get_prev_file(self) -> Optional[str]:
        """Get previous file in tab order."""
        if not self.tab_order or not self.active_file:
            return None
        idx = self.tab_order.index(self.active_file)
        prev_idx = (idx - 1) % len(self.tab_order)
        return self.tab_order[prev_idx]

    def get_file_at_index(self, index: int) -> Optional[str]:
        """Get file at specific index (0-based)."""
        if 0 <= index < len(self.tab_order):
            return self.tab_order[index]
        return None


@dataclass
class EditorState:
    """Global editor state managing panes and splits."""

    DEFAULT_PANE_ID = "main"

    panes: list[EditorPane] = field(default_factory=list)
    active_pane_id: Optional[str] = None
    split_orientation: str = "none"

    def __post_init__(self):
        if not self.panes:
            pane = EditorPane(id=self.DEFAULT_PANE_ID)
            self.panes.append(pane)
            self.active_pane_id = pane.id

    @property
    def active_pane(self) -> Optional[EditorPane]:
        for pane in self.panes:
            if pane.id == self.active_pane_id:
                return pane
        return self.panes[0] if self.panes else None

    @property
    def active_file(self) -> Optional[OpenFile]:
        pane = self.active_pane
        if pane and pane.active_file:
            return pane.open_files.get(pane.active_file)
        return None

    def get_pane_by_id(self, pane_id: str) -> Optional[EditorPane]:
        for pane in self.panes:
            if pane.id == pane_id:
                return pane
        return None


# =============================================================================
# Utility Functions
# =============================================================================


def path_to_tab_id(path: Path) -> str:
    """Convert file path to a valid tab ID."""
    return f"tab-{hashlib.md5(str(path).encode()).hexdigest()[:8]}"


def get_language(path: Path) -> Optional[str]:
    """Get language for syntax highlighting."""
    return LANG_MAP.get(path.suffix.lower())


# =============================================================================
# Widgets
# =============================================================================


class FileTree(DirectoryTree):
    """Custom file tree showing all files."""

    pass


class Terminal(Static):
    """PTY-based terminal widget with zsh support."""

    def __init__(self, working_dir: Path | None = None, **kwargs):
        super().__init__(**kwargs)
        self.working_dir = working_dir or Path.cwd()
        self.pty_fd: int | None = None
        self.pid: int | None = None
        self.pty_screen = pyte.Screen(120, 24)
        self.pty_stream = pyte.Stream(self.pty_screen)
        self._read_task: asyncio.Task | None = None

    def on_mount(self) -> None:
        self.start_shell()

    def start_shell(self) -> None:
        self.pid, self.pty_fd = pty.fork()

        if self.pid == 0:
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["COLORTERM"] = "truecolor"
            os.chdir(str(self.working_dir))
            os.execvpe("/bin/zsh", ["/bin/zsh", "-i"], env)
        else:
            flags = fcntl.fcntl(self.pty_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.pty_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            self.resize_pty(120, 24)
            self._read_task = asyncio.create_task(self._read_pty())

    def resize_pty(self, cols: int, rows: int) -> None:
        if self.pty_fd is not None:
            self.pty_screen.resize(rows, cols)
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.pty_fd, termios.TIOCSWINSZ, winsize)

    async def _read_pty(self) -> None:
        while self.pty_fd is not None:
            try:
                data = os.read(self.pty_fd, 65536)
                if data:
                    self.pty_stream.feed(data.decode("utf-8", errors="replace"))
                    self.refresh_display()
            except BlockingIOError:
                pass
            except OSError:
                break
            await asyncio.sleep(0.02)

    def refresh_display(self) -> None:
        lines = []
        for y in range(self.pty_screen.lines):
            line = Text()
            for x in range(self.pty_screen.columns):
                char = self.pty_screen.buffer[y][x]
                char_data = char.data if char.data else " "

                style_parts = []

                fg = char.fg
                if fg == "default":
                    fg_color = PYTE_COLORS["default"]
                elif fg in PYTE_COLORS:
                    fg_color = PYTE_COLORS[fg]
                elif fg in PYTE_BRIGHT_COLORS:
                    fg_color = PYTE_BRIGHT_COLORS[fg]
                elif isinstance(fg, str) and fg.startswith("#"):
                    fg_color = fg
                else:
                    fg_color = PYTE_COLORS["default"]
                style_parts.append(fg_color)

                bg = char.bg
                if bg != "default":
                    if bg in PYTE_COLORS:
                        style_parts.append(f"on {PYTE_COLORS[bg]}")
                    elif bg in PYTE_BRIGHT_COLORS:
                        style_parts.append(f"on {PYTE_BRIGHT_COLORS[bg]}")

                if char.bold:
                    style_parts.append("bold")
                if char.italics:
                    style_parts.append("italic")
                if char.underscore:
                    style_parts.append("underline")

                line.append(
                    char_data, style=" ".join(style_parts) if style_parts else None
                )

            line_str = str(line).rstrip()
            if line_str or y < self.pty_screen.lines - 1:
                lines.append(line)

        while lines and not str(lines[-1]).strip():
            lines.pop()

        result = Text()
        for i, line in enumerate(lines):
            result.append_text(line)
            if i < len(lines) - 1:
                result.append("\n")

        self.update(result)

    def send_key(self, key: str) -> None:
        if self.pty_fd is not None:
            try:
                os.write(self.pty_fd, key.encode("utf-8"))
            except OSError:
                pass

    def send_text(self, text: str) -> None:
        if self.pty_fd is not None:
            try:
                os.write(self.pty_fd, text.encode("utf-8"))
            except OSError:
                pass

    def on_unmount(self) -> None:
        if self._read_task:
            self._read_task.cancel()
        if self.pty_fd is not None:
            try:
                os.close(self.pty_fd)
            except OSError:
                pass
        if self.pid is not None:
            try:
                os.kill(self.pid, 9)
                os.waitpid(self.pid, 0)
            except OSError:
                pass


class TerminalInput(Static):
    """Terminal input widget that captures all keys."""

    can_focus = True

    def __init__(self, terminal: Terminal, **kwargs):
        super().__init__("", **kwargs)
        self.terminal = terminal

    def on_key(self, event) -> None:
        event.stop()

        key = event.key

        key_map = {
            "enter": "\r",
            "tab": "\t",
            "backspace": "\x7f",
            "delete": "\x1b[3~",
            "escape": "\x1b",
            "up": "\x1b[A",
            "down": "\x1b[B",
            "right": "\x1b[C",
            "left": "\x1b[D",
            "home": "\x1b[H",
            "end": "\x1b[F",
            "pageup": "\x1b[5~",
            "pagedown": "\x1b[6~",
            "ctrl+c": "\x03",
            "ctrl+d": "\x04",
            "ctrl+z": "\x1a",
            "ctrl+l": "\x0c",
            "ctrl+a": "\x01",
            "ctrl+e": "\x05",
            "ctrl+k": "\x0b",
            "ctrl+u": "\x15",
            "ctrl+r": "\x12",
        }

        if key in key_map:
            self.terminal.send_key(key_map[key])
        elif event.character and len(event.character) == 1:
            self.terminal.send_text(event.character)

    def render(self) -> Text:
        return Text("▌", style="blink")


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
            yield Input(id="search-input", placeholder="Find...")
            yield Button("↑", id="find-prev", classes="search-btn")
            yield Button("↓", id="find-next", classes="search-btn")
            yield Button("✕", id="close-search", classes="search-btn")
            yield Static("", id="search-status")

    def focus_input(self) -> None:
        """Focus the search input."""
        self.query_one("#search-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close-search":
            self.post_message(self.SearchClosed())
        elif event.button.id in ("find-next", "find-prev"):
            query = self.query_one("#search-input", Input).value
            if query:
                direction = "next" if event.button.id == "find-next" else "prev"
                self.post_message(self.SearchSubmitted(query, direction))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            query = event.value
            if query:
                self.post_message(self.SearchSubmitted(query, "next"))

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            query = event.value
            if query:
                self.post_message(self.SearchSubmitted(query, "next"))

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.post_message(self.SearchClosed())
            event.stop()

    def set_status(self, text: str) -> None:
        self.query_one("#search-status", Static).update(text)

    def set_query(self, text: str) -> None:
        self.query_one("#search-input", Input).value = text
        self.focus_input()


@dataclass
class MultiSelectState:
    """State for multi-select mode tracking."""
    
    target_text: str = ""
    # List of (row, col) positions that are highlighted
    highlighted_positions: list[tuple[int, int]] = field(default_factory=list)
    # Index of the "primary" selection (where user types)
    primary_idx: int = 0
    # Whether multi-select mode is active
    active: bool = False
    # Track the original selection position
    original_selection: tuple[int, int] = (0, 0)
    
    def reset(self) -> None:
        """Reset multi-select state."""
        self.target_text = ""
        self.highlighted_positions = []
        self.primary_idx = 0
        self.active = False
        self.original_selection = (0, 0)
    
    def add_position(self, row: int, col: int) -> bool:
        """Add a new position to highlight. Returns True if added."""
        pos = (row, col)
        if pos not in self.highlighted_positions:
            self.highlighted_positions.append(pos)
            return True
        return False
    
    @property
    def count(self) -> int:
        """Number of highlighted positions."""
        return len(self.highlighted_positions)


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
        **kwargs
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
        self._last_click_time: float = 0

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
        # 높이 자동 조정을 위해 styles.height 설정
        if self.expanded:
            # 미리보기 줄 수 + 헤더 1줄
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

    def on_click(self, event) -> None:
        """Handle click - header toggles expand, preview area opens file."""
        # 첫 번째 줄(헤더)인지 미리보기 영역인지 구분
        # 클릭 위치의 y 오프셋으로 판단
        if self.expanded and event.y > 0:
            # 펼쳐진 상태에서 미리보기 영역 클릭 → 파일 열기
            self.post_message(self.Selected(self.filepath, self.line_num))
        else:
            # 헤더 클릭 → 토글
            self.toggle_expand()

    def on_key(self, event) -> None:
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

    def __init__(self, root_path: Path, callback=None):
        super().__init__()
        self.root_path = root_path
        self.callback = callback
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
                yield Input(id="project-search-input", placeholder="Enter search term...")
                yield Button("Search", id="search-btn", variant="primary")
            yield VerticalScroll(id="project-search-results")
            with Horizontal(id="project-search-footer"):
                yield Static("Click Search or press Enter", id="result-count")
                yield Button("Open", id="open-file-btn")
                yield Button("Close", id="close-project-search")

    def on_mount(self) -> None:
        self.query_one("#project-search-input", Input).focus()

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
            # 검색 결과에서 Enter → 파일 열기
            focused.post_message(SearchResultItem.Selected(focused.filepath, focused.line_num))
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
        import subprocess
        
        self.app.notify("_do_search called")  # DEBUG
        search_text = self.query_one("#project-search-input", Input).value
        self.app.notify(f"search_text: {search_text}")  # DEBUG
        if not search_text or len(search_text) < 2:
            self.query_one("#result-count", Static).update("Enter at least 2 characters")
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
                    ["rg", "--line-number", "--no-heading", "--color=never",
                     "-m", "50", "-g", "!node_modules", "-g", "!.git",
                     "-g", "!__pycache__", "-g", "!*.min.*", "-g", "!.venv",
                     "--max-depth", "10",
                     search_text, str(self.root_path)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ["grep", "-rn", "-m", "50",
                     "--include=*.py", "--include=*.js", "--include=*.ts",
                     "--include=*.tsx", "--include=*.json", "--include=*.md",
                     "--exclude-dir=node_modules", "--exclude-dir=.git",
                     "--exclude-dir=__pycache__", "--exclude-dir=.venv",
                     search_text, str(self.root_path)],
                    capture_output=True,
                    text=True,
                    timeout=10
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
                            id=f"result-{len(self.results)-1}"
                        )
                        await results_container.mount(item)
                
                self.query_one("#result-count", Static).update(f"{len(self.results)} matches (click to preview)")
            else:
                self.query_one("#result-count", Static).update("No matches found")
        except subprocess.TimeoutExpired:
            self.query_one("#result-count", Static).update("Search timed out")
        except Exception as e:
            self.query_one("#result-count", Static).update(f"Error: {str(e)[:30]}")


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


class EditorPaneWidget(Container):
    """Single editor pane containing tabbed editors."""

    class PaneFocused(Message):
        """Message sent when pane receives focus."""

        def __init__(self, pane_id: str):
            super().__init__()
            self.pane_id = pane_id

    def __init__(self, pane_id: str, **kwargs):
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
                h for h in editor._highlights[line_num] 
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

    def on_focus(self, event) -> None:
        self.post_message(self.PaneFocused(self.pane_id))

    def on_click(self, event) -> None:
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
        editor = TextArea(
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

    def get_active_editor(self) -> Optional[TextArea]:
        """Get currently active editor."""
        tabs = self.query_one(f"#tabs-{self.pane_id}", TabbedContent)
        active_pane = tabs.active_pane
        if active_pane:
            try:
                return active_pane.query_one(TextArea)
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


# =============================================================================
# Main Application
# =============================================================================


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
        pane_widget = self.query_one(
            f"#pane-{pane.id}", EditorPaneWidget
        )
        self.call_later(
            lambda: asyncio.create_task(
                pane_widget.open_file(path, content, language)
            )
        )

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
            self.notify(f"Cannot move {direction}: already have {current_orientation} split", severity="warning")
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
        current_is_first = (pane.id == pane_ids[0])
        
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
            target_pane_widget = self.query_one(f"#pane-{target_pane.id}", EditorPaneWidget)
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
                pane_widget = self.query_one(
                    f"#pane-{pane.id}", EditorPaneWidget
                )
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
            current_pos = sum(len(lines[i]) + 1 for i in range(cursor_loc[0])) + cursor_loc[1]

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
                current_match = content[:pos + 1].count(search_text)
                
                # Update search bar status
                try:
                    search_bar = pane_widget.query_one(f"#search-bar-{pane.id}", SearchBar)
                    search_bar.set_status(f"{current_match}/{total_matches}")
                except Exception:
                    pass
            else:
                try:
                    search_bar = pane_widget.query_one(f"#search-bar-{pane.id}", SearchBar)
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
                            self.call_later(
                                lambda: self._goto_line(line_num)
                            )
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
                search_start = sum(len(lines[i]) + 1 for i in range(last_pos[0])) + last_pos[1] + len(ms.target_text)
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

    def _apply_multiselect_change(self, pane_widget: EditorPaneWidget, new_text: str) -> None:
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
                    new_text = line[orig_col:cursor[1]]
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
