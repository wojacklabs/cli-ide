"""Configuration settings for CLI-IDE."""

from __future__ import annotations

import logging
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..exceptions import ConfigError

logger = logging.getLogger(__name__)


@dataclass
class EditorConfig:
    """Editor-related settings."""

    theme: str = "light-ide"
    tab_size: int = 4
    show_line_numbers: bool = True


@dataclass
class TerminalConfig:
    """Terminal-related settings."""

    shell: str = ""  # Empty means use $SHELL
    height: int = 14

    def get_shell(self) -> str:
        """Get the shell to use."""
        if self.shell:
            return self.shell
        return os.environ.get("SHELL", "/bin/sh")


@dataclass
class SidebarConfig:
    """Sidebar-related settings."""

    width: int = 30
    visible: bool = True


@dataclass
class Config:
    """Main configuration class for CLI-IDE."""

    editor: EditorConfig = field(default_factory=EditorConfig)
    terminal: TerminalConfig = field(default_factory=TerminalConfig)
    sidebar: SidebarConfig = field(default_factory=SidebarConfig)

    # XDG config directory
    CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")) / "cli-ide"
    CONFIG_FILE = CONFIG_DIR / "config.toml"
    PROJECT_CONFIG_FILE = ".cli-ide.toml"

    @classmethod
    def load(cls, project_path: Optional[Path] = None) -> "Config":
        """Load configuration from files.

        Priority (highest to lowest):
        1. Project-specific config (.cli-ide.toml in project root)
        2. User config (~/.config/cli-ide/config.toml)
        3. Default values
        """
        config = cls()

        # Load user config
        if cls.CONFIG_FILE.exists():
            config._load_from_file(cls.CONFIG_FILE)

        # Load project config (overrides user config)
        if project_path:
            project_config = project_path / cls.PROJECT_CONFIG_FILE
            if project_config.exists():
                config._load_from_file(project_config)

        return config

    def _load_from_file(self, path: Path) -> None:
        """Load configuration from a TOML file.

        Args:
            path: Path to the TOML configuration file.

        Note:
            Invalid configurations are logged but don't raise exceptions.
            The application continues with default values.
        """
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
        except FileNotFoundError:
            return  # File doesn't exist, use defaults
        except tomllib.TOMLDecodeError as e:
            logger.warning("Invalid TOML in %s: %s", path, e)
            return
        except OSError as e:
            logger.warning("Cannot read config file %s: %s", path, e)
            return

        # Editor settings
        if "editor" in data:
            editor_data = data["editor"]
            if "theme" in editor_data:
                self.editor.theme = str(editor_data["theme"])
            if "tab_size" in editor_data:
                self.editor.tab_size = int(editor_data["tab_size"])
            if "show_line_numbers" in editor_data:
                self.editor.show_line_numbers = bool(editor_data["show_line_numbers"])

        # Terminal settings
        if "terminal" in data:
            terminal_data = data["terminal"]
            if "shell" in terminal_data:
                self.terminal.shell = str(terminal_data["shell"])
            if "height" in terminal_data:
                self.terminal.height = int(terminal_data["height"])

        # Sidebar settings
        if "sidebar" in data:
            sidebar_data = data["sidebar"]
            if "width" in sidebar_data:
                self.sidebar.width = int(sidebar_data["width"])
            if "visible" in sidebar_data:
                self.sidebar.visible = bool(sidebar_data["visible"])

    def save(self) -> None:
        """Save configuration to user config file."""
        self.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        content = f"""# CLI-IDE Configuration

[editor]
theme = "{self.editor.theme}"
tab_size = {self.editor.tab_size}
show_line_numbers = {str(self.editor.show_line_numbers).lower()}

[terminal]
shell = "{self.terminal.shell}"  # Empty string uses $SHELL
height = {self.terminal.height}

[sidebar]
width = {self.sidebar.width}
visible = {str(self.sidebar.visible).lower()}
"""
        with open(self.CONFIG_FILE, "w") as f:
            f.write(content)
