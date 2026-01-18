# CLI-IDE

Terminal-based IDE built with [Textual](https://textual.textualize.io/). Features a file explorer, tabbed code editor with syntax highlighting, and an integrated terminal.

## Features

- File explorer with directory tree navigation
- Tabbed code editor with syntax highlighting
- Split view (horizontal/vertical)
- Integrated terminal (PTY-based)
- Project-wide search (ripgrep or grep)
- Multi-select editing (Ctrl+I)
- Configurable via TOML files

## Requirements

- Python 3.11+
- Dependencies: `textual`, `pyte`, `rich`
- Optional: `ripgrep` for faster project search

## Installation

```bash
cd cli-ide
pip install -e .
```

Or with virtual environment:

```bash
cd cli-ide
python -m venv venv
source venv/bin/activate
pip install -e .
```

## Usage

```bash
# Open current directory
cli-ide

# Open specific directory
cli-ide /path/to/project

# Or run as module
python -m cli_ide.app /path/to/project
```

## Keyboard Shortcuts

### File Operations
| Key | Action |
|-----|--------|
| `Ctrl+S` | Save file |
| `Ctrl+Q` | Quit |

### Navigation
| Key | Action |
|-----|--------|
| `Ctrl+E` | Focus editor |
| `Ctrl+T` | Focus terminal |
| `Ctrl+B` | Toggle sidebar |
| `Alt+1-9` | Go to tab 1-9 |

### Tab Operations
| Key | Action |
|-----|--------|
| `Ctrl+W` | Close tab |

### Split View
| Key | Action |
|-----|--------|
| `Ctrl+Shift+Left` | Move file to left pane |
| `Ctrl+Shift+Right` | Move file to right pane |
| `Ctrl+Shift+Up` | Move file to top pane |
| `Ctrl+Shift+Down` | Move file to bottom pane |

### Search
| Key | Action |
|-----|--------|
| `Ctrl+F` | Find in file |
| `Ctrl+G` | Find in project |

### Editing
| Key | Action |
|-----|--------|
| `Ctrl+D` | Delete line |
| `Ctrl+I` | Select next match (multi-select) |
| `Enter` | Apply multi-select changes |
| `Escape` | Cancel multi-select |

## Configuration

Configuration files are loaded in the following order (later overrides earlier):

1. User config: `~/.config/cli-ide/config.toml`
2. Project config: `.cli-ide.toml` (in project root)

### Example Configuration

```toml
[editor]
theme = "light-ide"
tab_size = 4
show_line_numbers = true

[terminal]
shell = ""  # Empty uses $SHELL environment variable
height = 14

[sidebar]
width = 30
visible = true
```

## Project Structure

```
cli_ide/
├── __init__.py           # Package entry point
├── app.py                # Main CliIdeApp class
├── utils.py              # Utility functions
├── config/
│   ├── __init__.py
│   ├── defaults.py       # Language mappings, defaults
│   └── settings.py       # Config class (TOML loading)
├── models/
│   ├── __init__.py
│   └── state.py          # EditorState, OpenFile, etc.
├── themes/
│   ├── __init__.py
│   └── light.py          # Light theme definition
└── widgets/
    ├── __init__.py
    ├── dialogs.py        # SaveConfirmDialog
    ├── editor.py         # EditorPaneWidget, SplitContainer
    ├── file_tree.py      # FileTree
    ├── search.py         # SearchBar, ProjectSearchDialog
    └── terminal.py       # Terminal, TerminalInput
```

## License

MIT
