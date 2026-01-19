# Contributing to CLI-IDE

Thanks for your interest in contributing to CLI-IDE! This document provides guidelines for contributing.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- macOS or Linux (Windows is not currently supported due to PTY requirements)
- Optional: [ripgrep](https://github.com/BurntSushi/ripgrep) for faster project search

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/user/cli-ide.git
cd cli-ide

# Using uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Or using pip
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=cli_ide --cov-report=term-missing

# Run specific test file
pytest tests/test_models.py
```

### Running the Application

```bash
# Run from source
cli-ide

# Or as module
python -m cli_ide.app
```

## How to Contribute

### Reporting Bugs

1. Check if the issue already exists in [GitHub Issues](https://github.com/user/cli-ide/issues)
2. If not, create a new issue with:
   - Clear, descriptive title
   - Steps to reproduce
   - Expected vs actual behavior
   - Python version and OS
   - Relevant error messages or screenshots

### Suggesting Features

1. Open a [GitHub Issue](https://github.com/user/cli-ide/issues) with the `enhancement` label
2. Describe the feature and its use case
3. Discuss the implementation approach if you have ideas

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes following the code style guidelines
4. Add tests for new functionality
5. Ensure all tests pass:
   ```bash
   pytest
   ```
6. Commit with clear, descriptive messages
7. Push and open a Pull Request

## Code Style Guidelines

### General

- Use type hints for all function parameters and return values
- Write docstrings for classes and public functions
- Keep functions focused and reasonably sized
- Follow existing code patterns in the codebase

### Python Style

- Follow PEP 8
- Use `snake_case` for functions and variables
- Use `PascalCase` for classes
- Maximum line length: 100 characters

### Commit Messages

Write clear, concise commit messages:

```
Add multi-cursor support for batch editing

- Implement selection tracking in EditorState
- Add Ctrl+I binding for selecting next match
- Update TextArea to highlight all selections
```

### Code Organization

```
cli_ide/
├── config/      # Configuration loading and defaults
├── models/      # Data models and state management
├── themes/      # Visual themes
└── widgets/     # UI components (keep widgets focused and reusable)
```

## Architecture Overview

### Key Components

- **CliIdeApp** (`app.py`): Main application, handles global keybindings and layout
- **EditorState** (`models/state.py`): Centralized state for open files and panes
- **EditorPaneWidget** (`widgets/editor.py`): Individual editor pane with tabs
- **Terminal** (`widgets/terminal.py`): PTY-based terminal emulator
- **Config** (`config/settings.py`): TOML configuration loading

### Message Flow

Components communicate via Textual's message system:

```python
# Emitting a message
self.post_message(EditorPaneWidget.PaneFocused(pane_id))

# Handling a message
@on(EditorPaneWidget.PaneFocused)
def handle_pane_focused(self, event):
    self.state.active_pane_id = event.pane_id
```

## Areas Where Help is Needed

- [ ] Windows support (alternative to PTY)
- [ ] Additional themes (dark theme, popular color schemes)
- [ ] Language Server Protocol (LSP) integration
- [ ] Git integration (status, diff, blame)
- [ ] Plugin system architecture
- [ ] Performance optimization for large files
- [ ] Accessibility improvements
- [ ] Documentation and tutorials

## Questions?

Feel free to open an issue for any questions about contributing.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
