"""Light theme definitions for CLI-IDE."""

from rich.style import Style
from textual.widgets.text_area import TextAreaTheme

# Custom light theme for syntax highlighting (matching textual-light)
LIGHT_THEME = TextAreaTheme(
    name="light-ide",
    # Based on textual-light app theme colors:
    # Primary: #004578, Secondary: #0178D4, Accent: #ffa62b
    # Background: #E0E0E0, Surface: #D8D8D8, Panel: #D0D0D0
    # Error: #ba3c5b, Success: #4EBF71, Warning: #ffa62b
    base_style=Style(color="#1a1a1a", bgcolor="#E0E0E0"),
    gutter_style=Style(color="#666666", bgcolor="#D8D8D8"),
    cursor_style=Style(color="#ffffff", bgcolor="#004578"),
    cursor_line_style=Style(bgcolor="#D0D0D0"),
    cursor_line_gutter_style=Style(color="#1a1a1a", bgcolor="#D0D0D0"),
    bracket_matching_style=Style(bgcolor="#ffa62b", bold=True),
    selection_style=Style(bgcolor="#a8c8e8"),
    syntax_styles={
        # Text formatting
        "bold": Style(bold=True),
        "italic": Style(italic=True),
        "strikethrough": Style(strike=True),
        # Keywords - Primary color
        "keyword": Style(color="#004578", bold=True),
        "keyword.function": Style(color="#004578", bold=True),
        "keyword.return": Style(color="#004578", bold=True),
        "keyword.operator": Style(color="#004578"),
        "conditional": Style(color="#004578", bold=True),
        "repeat": Style(color="#004578", bold=True),
        "exception": Style(color="#ba3c5b", bold=True),
        "include": Style(color="#004578", bold=True),
        # Functions and methods - Secondary color
        "function": Style(color="#0178D4"),
        "function.call": Style(color="#0178D4"),
        "method": Style(color="#0178D4"),
        "method.call": Style(color="#0178D4"),
        # Classes and types
        "class": Style(color="#0178D4", bold=True),
        "type": Style(color="#0178D4"),
        "type.builtin": Style(color="#0178D4"),
        "type.class": Style(color="#0178D4", bold=True),
        # Strings - Success color (green)
        "string": Style(color="#4EBF71"),
        "string.documentation": Style(color="#4EBF71", italic=True),
        "inline_code": Style(color="#4EBF71"),
        # Numbers and constants - Accent color (orange)
        "number": Style(color="#b35900"),
        "float": Style(color="#b35900"),
        "boolean": Style(color="#004578", italic=True),
        "constant.builtin": Style(color="#b35900"),
        # Comments - Muted gray
        "comment": Style(color="#6a737d", italic=True),
        # Operators and punctuation
        "operator": Style(color="#ba3c5b"),
        "punctuation.bracket": Style(color="#1a1a1a"),
        "punctuation.delimiter": Style(color="#1a1a1a"),
        "punctuation.special": Style(color="#ba3c5b"),
        # Variables and parameters
        "variable": Style(color="#1a1a1a"),
        "variable.parameter": Style(color="#b35900"),
        "parameter": Style(color="#b35900"),
        # Markdown
        "heading": Style(color="#004578", bold=True),
        "heading.marker": Style(color="#666666"),
        "list.marker": Style(color="#666666"),
        "link.label": Style(color="#0178D4"),
        "link.uri": Style(color="#0178D4", underline=True),
        # Tags (HTML/XML) - Secondary color
        "tag": Style(color="#0178D4"),
        # JSON
        "json.label": Style(color="#004578", bold=True),
        # YAML
        "yaml.field": Style(color="#004578", bold=True),
        # TOML
        "toml.type": Style(color="#0178D4"),
        # CSS
        "css.property": Style(color="#004578"),
        # Custom multi-select highlight
        "multiselect": Style(bgcolor="#ffa62b", color="#000000"),
    },
)

# ANSI color mapping for pyte
PYTE_COLORS = {
    "black": "#24292e",
    "red": "#cf222e",
    "green": "#116329",
    "brown": "#953800",
    "blue": "#0550ae",
    "magenta": "#8250df",
    "cyan": "#0969da",
    "white": "#6e7781",
    "default": "#24292e",
}

PYTE_BRIGHT_COLORS = {
    "black": "#57606a",
    "red": "#ff8182",
    "green": "#4ac26b",
    "brown": "#d4a72c",
    "blue": "#54aeff",
    "magenta": "#c297ff",
    "cyan": "#76e3ea",
    "white": "#ffffff",
}
