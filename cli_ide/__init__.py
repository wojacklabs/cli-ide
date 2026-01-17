"""CLI-IDE: Terminal-based IDE with file explorer, code editor, and terminal.

This package provides both a complete IDE application and reusable components.

Quick Start (Application):
    ```python
    from cli_ide import CliIdeApp

    app = CliIdeApp("/path/to/project")
    app.run()
    ```

Using Individual Components:
    ```python
    from cli_ide.widgets import Terminal, EditorPaneWidget, FileTree
    from cli_ide.models import EditorState, OpenFile
    from cli_ide.config import Config
    ```
"""

__version__ = "0.1.0"

from .app import CliIdeApp
from .config import Config
from .exceptions import (
    CliIdeError,
    ConfigError,
    EditorError,
    FileOperationError,
    TerminalError,
)
from .models import EditorPane, EditorState, MultiSelectState, OpenFile

__all__ = [
    # Main application
    "CliIdeApp",
    # Configuration
    "Config",
    # Models
    "EditorState",
    "EditorPane",
    "OpenFile",
    "MultiSelectState",
    # Exceptions
    "CliIdeError",
    "ConfigError",
    "FileOperationError",
    "TerminalError",
    "EditorError",
    # Version
    "__version__",
]
