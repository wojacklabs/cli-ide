"""Terminal widget with PTY support."""

from __future__ import annotations

import asyncio
import fcntl
import os
import pty
import struct
import termios
from pathlib import Path

from rich.text import Text
from textual import events
from textual.widgets import Static

from ..themes import PYTE_BRIGHT_COLORS, PYTE_COLORS

# Import pyte lazily to allow module loading without it
try:
    import pyte
except ImportError:
    pyte = None


class Terminal(Static):
    """PTY-based terminal widget with shell support.

    A terminal emulator widget that spawns a real shell process.
    Can be used independently in any Textual application.

    Args:
        working_dir: Initial working directory for the shell.
            Defaults to current working directory.

    Example:
        ```python
        from textual.app import App, ComposeResult
        from cli_ide.widgets import Terminal, TerminalInput

        class MyApp(App):
            def compose(self) -> ComposeResult:
                terminal = Terminal(id="my-terminal")
                yield terminal
                yield TerminalInput(terminal)
        ```

    Note:
        Requires the `pyte` library for terminal emulation.
    """

    def __init__(self, working_dir: Path | None = None, **kwargs):
        super().__init__(**kwargs)
        self.working_dir = working_dir or Path.cwd()
        self.pty_fd: int | None = None
        self.pid: int | None = None
        if pyte:
            self.pty_screen = pyte.Screen(120, 24)
            self.pty_stream = pyte.Stream(self.pty_screen)
        else:
            self.pty_screen = None
            self.pty_stream = None
        self._read_task: asyncio.Task | None = None

    def on_mount(self) -> None:
        self.start_shell()

    def start_shell(self) -> None:
        if not pyte:
            self.update("Error: pyte library not installed")
            return

        self.pid, self.pty_fd = pty.fork()

        if self.pid == 0:
            env = os.environ.copy()
            env["TERM"] = "xterm-256color"
            env["COLORTERM"] = "truecolor"
            os.chdir(str(self.working_dir))
            # Use user's shell from environment, fallback to /bin/sh
            shell = os.environ.get("SHELL", "/bin/sh")
            os.execvpe(shell, [shell, "-i"], env)
        else:
            flags = fcntl.fcntl(self.pty_fd, fcntl.F_GETFL)
            fcntl.fcntl(self.pty_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
            self.resize_pty(120, 24)
            self._read_task = asyncio.create_task(self._read_pty())

    def resize_pty(self, cols: int, rows: int) -> None:
        if self.pty_fd is not None and self.pty_screen:
            self.pty_screen.resize(rows, cols)
            winsize = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(self.pty_fd, termios.TIOCSWINSZ, winsize)

    async def _read_pty(self) -> None:
        while self.pty_fd is not None:
            try:
                data = os.read(self.pty_fd, 65536)
                if data:
                    self.pty_stream.feed(data.decode("utf-8", errors="replace"))
                    self.refresh_display()
            except BlockingIOError:
                pass
            except OSError:
                break
            await asyncio.sleep(0.02)

    def refresh_display(self) -> None:
        if not self.pty_screen:
            return

        lines = []
        for y in range(self.pty_screen.lines):
            line = Text()
            for x in range(self.pty_screen.columns):
                char = self.pty_screen.buffer[y][x]
                char_data = char.data if char.data else " "

                style_parts = []

                fg = char.fg
                if fg == "default":
                    fg_color = PYTE_COLORS["default"]
                elif fg in PYTE_COLORS:
                    fg_color = PYTE_COLORS[fg]
                elif fg in PYTE_BRIGHT_COLORS:
                    fg_color = PYTE_BRIGHT_COLORS[fg]
                elif isinstance(fg, str) and fg.startswith("#"):
                    fg_color = fg
                else:
                    fg_color = PYTE_COLORS["default"]
                style_parts.append(fg_color)

                bg = char.bg
                if bg != "default":
                    if bg in PYTE_COLORS:
                        style_parts.append(f"on {PYTE_COLORS[bg]}")
                    elif bg in PYTE_BRIGHT_COLORS:
                        style_parts.append(f"on {PYTE_BRIGHT_COLORS[bg]}")

                if char.bold:
                    style_parts.append("bold")
                if char.italics:
                    style_parts.append("italic")
                if char.underscore:
                    style_parts.append("underline")

                line.append(
                    char_data, style=" ".join(style_parts) if style_parts else None
                )

            line_str = str(line).rstrip()
            if line_str or y < self.pty_screen.lines - 1:
                lines.append(line)

        while lines and not str(lines[-1]).strip():
            lines.pop()

        result = Text()
        for i, line in enumerate(lines):
            result.append_text(line)
            if i < len(lines) - 1:
                result.append("\n")

        self.update(result)

    def send_key(self, key: str) -> None:
        if self.pty_fd is not None:
            try:
                os.write(self.pty_fd, key.encode("utf-8"))
            except OSError:
                pass

    def send_text(self, text: str) -> None:
        if self.pty_fd is not None:
            try:
                os.write(self.pty_fd, text.encode("utf-8"))
            except OSError:
                pass

    def on_unmount(self) -> None:
        if self._read_task:
            self._read_task.cancel()
        if self.pty_fd is not None:
            try:
                os.close(self.pty_fd)
            except OSError:
                pass
        if self.pid is not None:
            try:
                os.kill(self.pid, 9)
                os.waitpid(self.pid, os.WNOHANG)
            except (OSError, ChildProcessError):
                pass


class TerminalInput(Static):
    """Terminal input widget that captures all keys."""

    can_focus = True

    def __init__(self, terminal: Terminal, **kwargs):
        super().__init__("", **kwargs)
        self.terminal = terminal

    def on_key(self, event: events.Key) -> None:
        event.stop()

        key = event.key

        key_map = {
            "enter": "\r",
            "tab": "\t",
            "backspace": "\x7f",
            "delete": "\x1b[3~",
            "escape": "\x1b",
            "up": "\x1b[A",
            "down": "\x1b[B",
            "right": "\x1b[C",
            "left": "\x1b[D",
            "home": "\x1b[H",
            "end": "\x1b[F",
            "pageup": "\x1b[5~",
            "pagedown": "\x1b[6~",
            "ctrl+c": "\x03",
            "ctrl+d": "\x04",
            "ctrl+z": "\x1a",
            "ctrl+l": "\x0c",
            "ctrl+a": "\x01",
            "ctrl+e": "\x05",
            "ctrl+k": "\x0b",
            "ctrl+u": "\x15",
            "ctrl+r": "\x12",
        }

        if key in key_map:
            self.terminal.send_key(key_map[key])
        elif event.character and len(event.character) == 1:
            self.terminal.send_text(event.character)

    def render(self) -> Text:
        return Text("▌", style="blink")
