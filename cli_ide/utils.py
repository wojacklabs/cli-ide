"""Utility functions for CLI-IDE."""

import hashlib
from pathlib import Path
from typing import Optional

from .config.defaults import LANG_MAP


def path_to_tab_id(path: Path) -> str:
    """Convert file path to a valid tab ID."""
    return f"tab-{hashlib.md5(str(path).encode()).hexdigest()[:8]}"


def get_language(path: Path) -> Optional[str]:
    """Get language for syntax highlighting."""
    return LANG_MAP.get(path.suffix.lower())
