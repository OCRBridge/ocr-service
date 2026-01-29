#!/usr/bin/env python3
"""
System dependency checker for OCR service.
Validates required system libraries are installed before running the service.

This script can be run standalone (without uv/venv) to verify dependencies
before installation.

Exit codes:
    0: All dependencies satisfied
    1: Missing dependencies or incompatible Python version
"""

import ctypes.util
import platform
import sys


# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_header(message: str) -> None:
    """Print a bold header message."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}=== {message} ==={Colors.RESET}")


def print_success(message: str) -> None:
    """Print a success message in green."""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str) -> None:
    """Print an error message in red."""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def check_python_version() -> bool:
    """
    Check if Python version meets minimum requirements (>= 3.10).

    Returns:
        True if Python version is compatible, False otherwise.
    """
    required_version = (3, 10)
    current_version = sys.version_info[:2]

    if current_version >= required_version:
        print_success(f"Python {current_version[0]}.{current_version[1]} (required: >= 3.10)")
        return True
    else:
        print_error(
            f"Python {current_version[0]}.{current_version[1]} is too old (required: >= 3.10)"
        )
        print(f"\n{Colors.YELLOW}Please upgrade Python:{Colors.RESET}")
        print("  - Download from: https://www.python.org/downloads/")
        print("  - Or use pyenv: https://github.com/pyenv/pyenv")
        return False


def check_libmagic() -> bool:
    """
    Check if libmagic is installed and accessible.

    Returns:
        True if libmagic is found, False otherwise.
    """
    import os
    import subprocess

    # Try standard library detection first
    libmagic_path = ctypes.util.find_library("magic")

    if libmagic_path:
        print_success(f"libmagic found at: {libmagic_path}")
        return True

    # On macOS, Homebrew libraries aren't always found by ctypes.util.find_library
    # Try to load the library directly via python-magic to verify it works
    if platform.system() == "Darwin":
        # Check if Homebrew has libmagic installed
        try:
            brew_prefix = subprocess.run(
                ["brew", "--prefix", "libmagic"], capture_output=True, text=True, timeout=5
            )
            if brew_prefix.returncode == 0:
                brew_path = brew_prefix.stdout.strip()
                lib_path = os.path.join(brew_path, "lib", "libmagic.dylib")
                if os.path.exists(lib_path):
                    print_success(f"libmagic found at: {lib_path} (via Homebrew)")
                    return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Final attempt: Try to actually use python-magic if it's installed
    try:
        import magic

        # Try to create a Magic instance - this will fail if libmagic isn't available
        magic.Magic()
        print_success("libmagic is accessible via python-magic")
        return True
    except (ImportError, OSError):
        pass

    print_error("libmagic not found")
    return False


def get_libmagic_install_instructions() -> str:
    """
    Get OS-specific installation instructions for libmagic.

    Returns:
        Formatted installation instructions for the current OS.
    """
    system = platform.system()

    instructions = {
        "Darwin": """
{yellow}macOS Installation:{reset}
  Install libmagic using Homebrew:
    {bold}brew install libmagic{reset}
  
  If you don't have Homebrew, install it from: https://brew.sh
""",
        "Linux": """
{yellow}Linux Installation:{reset}
  
  {bold}Ubuntu/Debian:{reset}
    sudo apt-get update
    sudo apt-get install libmagic1
  
  {bold}Fedora/RHEL/CentOS:{reset}
    sudo dnf install file-libs
    # Or on older systems: sudo yum install file-libs
  
  {bold}Arch Linux:{reset}
    sudo pacman -S file
""",
        "Windows": """
{yellow}Windows Installation:{reset}
  
  {bold}Option 1 - Use python-magic-bin (Recommended):{reset}
    Instead of python-magic, install python-magic-bin which bundles libmagic:
    pip uninstall python-magic
    pip install python-magic-bin
  
  {bold}Option 2 - Manual Installation:{reset}
    1. Install MSYS2 from: https://www.msys2.org/
    2. In MSYS2 terminal: pacman -S mingw-w64-x86_64-file
    3. Add C:\\msys64\\mingw64\\bin to your PATH
  
  {bold}Note:{reset} Docker is recommended for Windows users.
""",
    }

    # Get instructions for current OS, or generic Linux instructions as fallback
    instruction = instructions.get(system, instructions["Linux"])

    # Format with colors
    return instruction.format(yellow=Colors.YELLOW, bold=Colors.BOLD, reset=Colors.RESET)


def main() -> int:
    """
    Main function to check all system dependencies.

    Returns:
        Exit code: 0 if all checks pass, 1 if any check fails.
    """
    print_header("Checking System Dependencies for OCR Service")

    all_checks_passed = True

    # Check Python version
    if not check_python_version():
        all_checks_passed = False

    # Check libmagic
    if not check_libmagic():
        all_checks_passed = False
        print(get_libmagic_install_instructions())

    # Print final result
    print()
    if all_checks_passed:
        print_success("All system dependencies are satisfied!")
        print(f"\n{Colors.GREEN}You can now run:{Colors.RESET}")
        print(f"  {Colors.BOLD}make install{Colors.RESET}  # Install Python dependencies")
        print(f"  {Colors.BOLD}make dev{Colors.RESET}      # Start development server")
        return 0
    else:
        print_error("Some dependencies are missing. Please install them and try again.")
        print(
            f"\n{Colors.YELLOW}After installing dependencies, run this check again:{Colors.RESET}"
        )
        print(f"  {Colors.BOLD}make check-deps{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
