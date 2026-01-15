"""Custom exceptions for CLI-IDE.

This module defines the exception hierarchy for CLI-IDE, allowing users
to catch and handle library-specific errors.

Example:
    ```python
    from cli_ide.exceptions import CliIdeError, ConfigError

    try:
        config = Config.load()
    except ConfigError as e:
        print(f"Configuration error: {e}")
    ```
"""


class CliIdeError(Exception):
    """Base exception for all CLI-IDE errors.

    All exceptions raised by CLI-IDE inherit from this class,
    making it easy to catch all library-specific errors.
    """

    pass


class ConfigError(CliIdeError):
    """Error related to configuration loading or validation.

    Raised when:
    - Configuration file is malformed
    - Configuration values are invalid
    - Required configuration is missing
    """

    pass


class FileOperationError(CliIdeError):
    """Error during file operations.

    Raised when:
    - File cannot be opened (permissions, encoding)
    - File cannot be saved
    - Path is invalid
    """

    pass


class TerminalError(CliIdeError):
    """Error related to terminal operations.

    Raised when:
    - PTY creation fails
    - Shell process cannot be started
    - Terminal communication fails
    """

    pass


class EditorError(CliIdeError):
    """Error related to editor operations.

    Raised when:
    - Tab operations fail
    - Editor state becomes inconsistent
    """

    pass
