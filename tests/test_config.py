"""Tests for CLI-IDE configuration."""

import os
import tempfile
from pathlib import Path

import pytest

from cli_ide.config import Config, LANG_MAP
from cli_ide.config.settings import EditorConfig, SidebarConfig, TerminalConfig


class TestLangMap:
    """Tests for language mapping."""

    def test_python_extension(self):
        """Python files should map to python."""
        assert LANG_MAP[".py"] == "python"

    def test_javascript_extensions(self):
        """JavaScript-related files should map to javascript."""
        assert LANG_MAP[".js"] == "javascript"
        assert LANG_MAP[".ts"] == "javascript"
        assert LANG_MAP[".tsx"] == "javascript"
        assert LANG_MAP[".jsx"] == "javascript"

    def test_json_extension(self):
        """JSON files should map to json."""
        assert LANG_MAP[".json"] == "json"

    def test_markdown_extension(self):
        """Markdown files should map to markdown."""
        assert LANG_MAP[".md"] == "markdown"


class TestEditorConfig:
    """Tests for EditorConfig dataclass."""

    def test_default_values(self):
        """EditorConfig should have sensible defaults."""
        config = EditorConfig()

        assert config.theme == "light-ide"
        assert config.tab_size == 4
        assert config.show_line_numbers is True


class TestTerminalConfig:
    """Tests for TerminalConfig dataclass."""

    def test_default_values(self):
        """TerminalConfig should have sensible defaults."""
        config = TerminalConfig()

        assert config.shell == ""
        assert config.height == 14

    def test_get_shell_uses_env(self):
        """get_shell should use SHELL environment variable."""
        config = TerminalConfig()
        original_shell = os.environ.get("SHELL")

        os.environ["SHELL"] = "/bin/zsh"
        assert config.get_shell() == "/bin/zsh"

        if original_shell:
            os.environ["SHELL"] = original_shell

    def test_get_shell_uses_configured(self):
        """get_shell should prefer configured shell."""
        config = TerminalConfig(shell="/bin/fish")

        assert config.get_shell() == "/bin/fish"


class TestSidebarConfig:
    """Tests for SidebarConfig dataclass."""

    def test_default_values(self):
        """SidebarConfig should have sensible defaults."""
        config = SidebarConfig()

        assert config.width == 30
        assert config.visible is True


class TestConfig:
    """Tests for main Config class."""

    def test_load_returns_config(self):
        """Config.load should return a Config instance."""
        config = Config.load()

        assert isinstance(config, Config)
        assert isinstance(config.editor, EditorConfig)
        assert isinstance(config.terminal, TerminalConfig)
        assert isinstance(config.sidebar, SidebarConfig)

    def test_load_with_project_path(self):
        """Config.load should accept project_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = Config.load(Path(tmpdir))

            assert isinstance(config, Config)

    def test_config_file_paths(self):
        """Config should define standard config paths."""
        assert Config.CONFIG_FILE.name == "config.toml"
        assert Config.PROJECT_CONFIG_FILE == ".cli-ide.toml"
