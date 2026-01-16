"""Widget components for CLI-IDE."""

from .dialogs import SaveConfirmDialog
from .editor import EditorPaneWidget, SplitContainer
from .file_tree import FileTree
from .search import ProjectSearchDialog, SearchBar, SearchResultItem
from .terminal import Terminal, TerminalInput

__all__ = [
    "Terminal",
    "TerminalInput",
    "FileTree",
    "SearchBar",
    "SearchResultItem",
    "ProjectSearchDialog",
    "SaveConfirmDialog",
    "EditorPaneWidget",
    "SplitContainer",
]
