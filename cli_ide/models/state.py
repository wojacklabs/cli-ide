"""State models for CLI-IDE editor."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


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
            try:
                idx = self.tab_order.index(path_str)
                self.tab_order.remove(path_str)
            except ValueError:
                idx = 0

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
        try:
            idx = self.tab_order.index(self.active_file)
        except ValueError:
            return self.tab_order[0] if self.tab_order else None
        next_idx = (idx + 1) % len(self.tab_order)
        return self.tab_order[next_idx]

    def get_prev_file(self) -> Optional[str]:
        """Get previous file in tab order."""
        if not self.tab_order or not self.active_file:
            return None
        try:
            idx = self.tab_order.index(self.active_file)
        except ValueError:
            return self.tab_order[-1] if self.tab_order else None
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
