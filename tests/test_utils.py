"""Tests for CLI-IDE utilities."""

from pathlib import Path

import pytest

from cli_ide.utils import get_language, path_to_tab_id


class TestPathToTabId:
    """Tests for path_to_tab_id function."""

    def test_returns_string(self):
        """path_to_tab_id should return a string."""
        result = path_to_tab_id(Path("/test.py"))
        assert isinstance(result, str)

    def test_starts_with_tab_prefix(self):
        """path_to_tab_id should start with 'tab-'."""
        result = path_to_tab_id(Path("/test.py"))
        assert result.startswith("tab-")

    def test_same_path_same_id(self):
        """Same path should produce same ID."""
        path = Path("/some/file.py")
        id1 = path_to_tab_id(path)
        id2 = path_to_tab_id(path)
        assert id1 == id2

    def test_different_paths_different_ids(self):
        """Different paths should produce different IDs."""
        id1 = path_to_tab_id(Path("/a.py"))
        id2 = path_to_tab_id(Path("/b.py"))
        assert id1 != id2


class TestGetLanguage:
    """Tests for get_language function."""

    def test_python_file(self):
        """Python files should return 'python'."""
        assert get_language(Path("/test.py")) == "python"

    def test_javascript_file(self):
        """JavaScript files should return 'javascript'."""
        assert get_language(Path("/test.js")) == "javascript"

    def test_typescript_file(self):
        """TypeScript files should return 'javascript'."""
        assert get_language(Path("/test.ts")) == "javascript"

    def test_json_file(self):
        """JSON files should return 'json'."""
        assert get_language(Path("/test.json")) == "json"

    def test_unknown_extension(self):
        """Unknown extensions should return None."""
        assert get_language(Path("/test.xyz")) is None

    def test_case_insensitive(self):
        """Extension matching should be case insensitive."""
        assert get_language(Path("/test.PY")) == "python"
        assert get_language(Path("/test.Py")) == "python"
