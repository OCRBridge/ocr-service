"""Unit tests for Tesseract engine utilities."""

from unittest.mock import Mock, patch

from src.services.ocr.engines.tesseract import (
    DEFAULT_TESSERACT_LANGUAGES,
    TesseractConfig,
    build_tesseract_config,
    get_installed_languages,
)

# ==============================================================================
# Tesseract Language Detection Tests
# ==============================================================================


def test_get_installed_languages_success():
    """Test successful tesseract language detection."""
    mock_output = "List of available languages (3):\neng\nfra\ndeu\n"

    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_run.return_value = mock_result

        # Clear cache before test
        get_installed_languages.cache_clear()

        languages = get_installed_languages()

        assert "eng" in languages
        assert "fra" in languages
        assert "deu" in languages
        # Should also include defaults
        assert DEFAULT_TESSERACT_LANGUAGES.issubset(languages)


def test_get_installed_languages_command_not_found():
    """Test fallback when tesseract command not found."""
    with patch("subprocess.run", side_effect=FileNotFoundError):
        get_installed_languages.cache_clear()

        languages = get_installed_languages()

        # Should return default languages
        assert languages == DEFAULT_TESSERACT_LANGUAGES


def test_get_installed_languages_command_fails():
    """Test fallback when tesseract command fails."""
    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: tesseract not found"
        mock_run.return_value = mock_result

        get_installed_languages.cache_clear()

        languages = get_installed_languages()

        # Should return default languages
        assert languages == DEFAULT_TESSERACT_LANGUAGES


def test_get_installed_languages_timeout():
    """Test fallback when tesseract command times out."""
    import subprocess

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("tesseract", 5)):
        get_installed_languages.cache_clear()

        languages = get_installed_languages()

        # Should return default languages
        assert languages == DEFAULT_TESSERACT_LANGUAGES


def test_get_installed_languages_cached():
    """Test that language detection is cached."""
    mock_output = "List of available languages (1):\neng\n"

    with patch("subprocess.run") as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = mock_output
        mock_run.return_value = mock_result

        get_installed_languages.cache_clear()

        # First call
        languages1 = get_installed_languages()
        # Second call
        languages2 = get_installed_languages()

        # Should only call subprocess once
        assert mock_run.call_count == 1
        assert languages1 == languages2

def test_default_tesseract_languages_constant():
    """Test that DEFAULT_TESSERACT_LANGUAGES contains common languages."""
    assert "eng" in DEFAULT_TESSERACT_LANGUAGES
    assert "fra" in DEFAULT_TESSERACT_LANGUAGES
    assert "deu" in DEFAULT_TESSERACT_LANGUAGES
    assert "spa" in DEFAULT_TESSERACT_LANGUAGES
    assert len(DEFAULT_TESSERACT_LANGUAGES) >= 5


# ==============================================================================
# Tesseract Config Building Tests
# ==============================================================================


def test_build_tesseract_config_all_defaults():
    """Test config building with all default values."""
    config = build_tesseract_config()

    assert config.lang == "eng"
    assert config.config_string == ""  # No options specified


def test_build_tesseract_config_custom_lang():
    """Test config building with custom language."""
    config = build_tesseract_config(lang="fra")

    assert config.lang == "fra"
    assert config.config_string == ""

def test_build_tesseract_config_with_psm():
    """Test config building with PSM parameter."""
    config = build_tesseract_config(psm=6)

    assert config.lang == "eng"
    assert "--psm 6" in config.config_string

def test_build_tesseract_config_with_oem():
    """Test config building with OEM parameter."""
    config = build_tesseract_config(oem=1)

    assert config.lang == "eng"
    assert "--oem 1" in config.config_string

def test_build_tesseract_config_with_dpi():
    """Test config building with DPI parameter."""
    config = build_tesseract_config(dpi=300)

    assert config.lang == "eng"
    assert "--dpi 300" in config.config_string

def test_build_tesseract_config_all_params():
    """Test config building with all parameters specified."""
    config = build_tesseract_config(lang="eng+fra", psm=3, oem=1, dpi=300)

    assert config.lang == "eng+fra"
    assert "--psm 3" in config.config_string
    assert "--oem 1" in config.config_string
    assert "--dpi 300" in config.config_string

def test_build_tesseract_config_none_params():
    """Test that None parameters are omitted from config string."""
    config = build_tesseract_config(lang="deu", psm=None, oem=None, dpi=None)

    assert config.lang == "deu"
    assert config.config_string == ""
    assert "psm" not in config.config_string
    assert "oem" not in config.config_string
    assert "dpi" not in config.config_string

def test_build_tesseract_config_ordering():
    """Test that config options maintain consistent ordering."""
    config = build_tesseract_config(dpi=300, psm=6, oem=1)

    # Options should appear in specific order: psm, oem, dpi
    parts = config.config_string.split()
    assert parts.index("--psm") < parts.index("--oem")
    assert parts.index("--oem") < parts.index("--dpi")

def test_tesseract_config_dataclass():
    """Test TesseractConfig dataclass structure."""
    config = TesseractConfig(lang="eng", config_string="--psm 3")

    assert isinstance(config, TesseractConfig)
    assert config.lang == "eng"
    assert config.config_string == "--psm 3"
