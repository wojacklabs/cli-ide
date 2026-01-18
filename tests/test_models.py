"""Tests for CLI-IDE models."""

from pathlib import Path

import pytest

from cli_ide.models import EditorPane, EditorState, MultiSelectState, OpenFile


class TestOpenFile:
    """Tests for OpenFile dataclass."""

    def test_is_modified_false_when_unchanged(self):
        """File should not be marked modified when content matches original."""
        f = OpenFile(
            path=Path("/test.py"),
            content="hello",
            original_content="hello",
        )
        assert f.is_modified is False

    def test_is_modified_true_when_changed(self):
        """File should be marked modified when content differs."""
        f = OpenFile(
            path=Path("/test.py"),
            content="hello world",
            original_content="hello",
        )
        assert f.is_modified is True

    def test_display_name_without_modification(self):
        """Display name should be filename when not modified."""
        f = OpenFile(
            path=Path("/path/to/test.py"),
            content="hello",
            original_content="hello",
        )
        assert f.display_name == "test.py"

    def test_display_name_with_modification(self):
        """Display name should have asterisk when modified."""
        f = OpenFile(
            path=Path("/path/to/test.py"),
            content="changed",
            original_content="hello",
        )
        assert f.display_name == "* test.py"


class TestEditorPane:
    """Tests for EditorPane dataclass."""

    def test_add_file(self):
        """Adding a file should update open_files and tab_order."""
        pane = EditorPane()
        f = OpenFile(Path("/test.py"), "content", "content")
        pane.add_file(f)

        assert "/test.py" in pane.open_files
        assert "/test.py" in pane.tab_order
        assert pane.active_file == "/test.py"

    def test_add_file_twice_does_not_duplicate(self):
        """Adding same file twice should not duplicate in tab_order."""
        pane = EditorPane()
        f = OpenFile(Path("/test.py"), "content", "content")
        pane.add_file(f)
        pane.add_file(f)

        assert pane.tab_order.count("/test.py") == 1

    def test_remove_file(self):
        """Removing a file should update state correctly."""
        pane = EditorPane()
        f1 = OpenFile(Path("/a.py"), "a", "a")
        f2 = OpenFile(Path("/b.py"), "b", "b")
        pane.add_file(f1)
        pane.add_file(f2)

        next_file = pane.remove_file(Path("/b.py"))

        assert "/b.py" not in pane.open_files
        assert "/b.py" not in pane.tab_order
        assert next_file == "/a.py"

    def test_remove_file_returns_none_when_empty(self):
        """Removing last file should return None."""
        pane = EditorPane()
        f = OpenFile(Path("/test.py"), "content", "content")
        pane.add_file(f)

        next_file = pane.remove_file(Path("/test.py"))

        assert next_file is None
        assert len(pane.tab_order) == 0

    def test_get_next_file(self):
        """get_next_file should cycle through tabs."""
        pane = EditorPane()
        pane.add_file(OpenFile(Path("/a.py"), "a", "a"))
        pane.add_file(OpenFile(Path("/b.py"), "b", "b"))
        pane.add_file(OpenFile(Path("/c.py"), "c", "c"))
        pane.active_file = "/a.py"

        assert pane.get_next_file() == "/b.py"

    def test_get_next_file_wraps(self):
        """get_next_file should wrap to first tab."""
        pane = EditorPane()
        pane.add_file(OpenFile(Path("/a.py"), "a", "a"))
        pane.add_file(OpenFile(Path("/b.py"), "b", "b"))
        pane.active_file = "/b.py"

        assert pane.get_next_file() == "/a.py"

    def test_get_prev_file(self):
        """get_prev_file should go backwards through tabs."""
        pane = EditorPane()
        pane.add_file(OpenFile(Path("/a.py"), "a", "a"))
        pane.add_file(OpenFile(Path("/b.py"), "b", "b"))
        pane.active_file = "/b.py"

        assert pane.get_prev_file() == "/a.py"

    def test_get_next_file_handles_invalid_active(self):
        """get_next_file should handle invalid active_file gracefully."""
        pane = EditorPane()
        pane.add_file(OpenFile(Path("/a.py"), "a", "a"))
        pane.active_file = "/nonexistent.py"

        # Should not raise, should return first file
        result = pane.get_next_file()
        assert result == "/a.py"

    def test_get_file_at_index(self):
        """get_file_at_index should return correct file."""
        pane = EditorPane()
        pane.add_file(OpenFile(Path("/a.py"), "a", "a"))
        pane.add_file(OpenFile(Path("/b.py"), "b", "b"))

        assert pane.get_file_at_index(0) == "/a.py"
        assert pane.get_file_at_index(1) == "/b.py"
        assert pane.get_file_at_index(2) is None


class TestEditorState:
    """Tests for EditorState dataclass."""

    def test_default_pane_created(self):
        """EditorState should create a default pane on init."""
        state = EditorState()

        assert len(state.panes) == 1
        assert state.active_pane_id == "main"

    def test_active_pane_property(self):
        """active_pane should return the active pane."""
        state = EditorState()

        assert state.active_pane is not None
        assert state.active_pane.id == "main"

    def test_active_file_property(self):
        """active_file should return the active file in active pane."""
        state = EditorState()
        f = OpenFile(Path("/test.py"), "content", "content")
        state.active_pane.add_file(f)

        assert state.active_file is not None
        assert state.active_file.path == Path("/test.py")

    def test_get_pane_by_id(self):
        """get_pane_by_id should find pane by ID."""
        state = EditorState()

        assert state.get_pane_by_id("main") is not None
        assert state.get_pane_by_id("nonexistent") is None


class TestMultiSelectState:
    """Tests for MultiSelectState dataclass."""

    def test_initial_state(self):
        """MultiSelectState should start inactive."""
        ms = MultiSelectState()

        assert ms.active is False
        assert ms.count == 0
        assert ms.target_text == ""

    def test_add_position(self):
        """add_position should add unique positions."""
        ms = MultiSelectState()
        ms.active = True

        assert ms.add_position(0, 5) is True
        assert ms.add_position(1, 10) is True
        assert ms.add_position(0, 5) is False  # Duplicate

        assert ms.count == 2

    def test_reset(self):
        """reset should clear all state."""
        ms = MultiSelectState()
        ms.active = True
        ms.target_text = "test"
        ms.add_position(0, 5)

        ms.reset()

        assert ms.active is False
        assert ms.target_text == ""
        assert ms.count == 0
