"""Unit tests for platform detection utilities.

Tests for macOS detection and platform name retrieval.
"""

from unittest.mock import patch

from src.utils.platform import get_platform_name, is_macos


def test_is_macos_on_darwin():
    """Test that is_macos returns True on macOS (Darwin)."""
    with patch("platform.system", return_value="Darwin"):
        assert is_macos() is True


def test_is_macos_on_linux():
    """Test that is_macos returns False on Linux."""
    with patch("platform.system", return_value="Linux"):
        assert is_macos() is False


def test_is_macos_on_windows():
    """Test that is_macos returns False on Windows."""
    with patch("platform.system", return_value="Windows"):
        assert is_macos() is False


def test_get_platform_name_darwin():
    """Test getting platform name on macOS."""
    with patch("platform.system", return_value="Darwin"):
        platform_name = get_platform_name()
        assert platform_name == "darwin"


def test_get_platform_name_linux():
    """Test getting platform name on Linux."""
    with patch("platform.system", return_value="Linux"):
        platform_name = get_platform_name()
        assert platform_name == "linux"


def test_get_platform_name_windows():
    """Test getting platform name on Windows."""
    with patch("platform.system", return_value="Windows"):
        platform_name = get_platform_name()
        assert platform_name == "windows"


def test_get_platform_name_lowercase():
    """Test that platform name is returned in lowercase."""
    with patch("platform.system", return_value="DARWIN"):
        platform_name = get_platform_name()
        assert platform_name == "darwin"
        assert platform_name.islower()


def test_get_platform_name_unknown():
    """Test getting platform name for unknown/unusual platform."""
    with patch("platform.system", return_value="FreeBSD"):
        platform_name = get_platform_name()
        assert platform_name == "freebsd"


def test_platform_module_imported():
    """Test that platform module is properly imported."""
    from src.utils import platform as platform_utils

    assert hasattr(platform_utils, "is_macos")
    assert hasattr(platform_utils, "get_platform_name")
    assert callable(platform_utils.is_macos)
    assert callable(platform_utils.get_platform_name)
