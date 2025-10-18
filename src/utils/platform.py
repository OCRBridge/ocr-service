"""Platform detection utilities."""

import platform


def is_macos() -> bool:
    """Check if running on macOS."""
    return platform.system() == "Darwin"


def get_platform_name() -> str:
    """Get platform name for error messages."""
    return platform.system().lower()
