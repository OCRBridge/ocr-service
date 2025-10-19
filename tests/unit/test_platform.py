"""Unit tests for platform detection utilities."""

import platform
from unittest.mock import patch

from src.utils.platform import get_platform_name, is_macos


class TestPlatformDetection:
    """Tests for platform detection functions."""

    @patch("platform.system")
    def test_is_macos_on_darwin(self, mock_system):
        """Test is_macos returns True on macOS."""
        mock_system.return_value = "Darwin"
        assert is_macos() is True

    @patch("platform.system")
    def test_is_macos_on_linux(self, mock_system):
        """Test is_macos returns False on Linux."""
        mock_system.return_value = "Linux"
        assert is_macos() is False

    @patch("platform.system")
    def test_is_macos_on_windows(self, mock_system):
        """Test is_macos returns False on Windows."""
        mock_system.return_value = "Windows"
        assert is_macos() is False

    @patch("platform.system")
    def test_get_platform_name_darwin(self, mock_system):
        """Test get_platform_name returns 'darwin' on macOS."""
        mock_system.return_value = "Darwin"
        assert get_platform_name() == "darwin"

    @patch("platform.system")
    def test_get_platform_name_linux(self, mock_system):
        """Test get_platform_name returns 'linux' on Linux."""
        mock_system.return_value = "Linux"
        assert get_platform_name() == "linux"

    @patch("platform.system")
    def test_get_platform_name_windows(self, mock_system):
        """Test get_platform_name returns 'windows' on Windows."""
        mock_system.return_value = "Windows"
        assert get_platform_name() == "windows"

    def test_actual_platform_detection(self):
        """Test that platform detection works with real system."""
        # This test verifies platform detection works on the actual system
        current_platform = platform.system()
        if current_platform == "Darwin":
            assert is_macos() is True
            assert get_platform_name() == "darwin"
        else:
            assert is_macos() is False
            assert get_platform_name() == current_platform.lower()
