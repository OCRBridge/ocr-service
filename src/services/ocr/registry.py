"""OCR engine registry for capability detection and caching."""

import platform
from dataclasses import dataclass
from typing import Optional

from src.models.job import EngineType


@dataclass
class EngineCapabilities:
    """Cached capabilities for an OCR engine."""

    available: bool  # Whether engine is currently available
    version: str | None  # Engine version (e.g., "5.3.0", "0.1.0")
    supported_languages: set[str]  # Set of supported language codes
    platform_requirement: str | None  # Required platform (e.g., "darwin" for macOS)


class EngineRegistry:
    """Singleton registry for OCR engine discovery and capability caching."""

    _instance: Optional["EngineRegistry"] = None
    _capabilities: dict[EngineType, EngineCapabilities]
    _initialized: bool = False

    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize registry and detect engines (once)."""
        if not self._initialized:
            self._capabilities = {}
            self._detect_all_engines()
            self._initialized = True

    def _detect_all_engines(self):
        """Detect all supported engines at startup."""
        self._detect_tesseract()
        self._detect_ocrmac()
        self._detect_easyocr()

    def _detect_tesseract(self):
        """Detect Tesseract availability and capabilities."""
        try:
            import pytesseract  # type: ignore[import-untyped]

            version = pytesseract.get_tesseract_version()
            languages = pytesseract.get_languages()
            self._capabilities[EngineType.TESSERACT] = EngineCapabilities(
                available=True,
                version=str(version),
                supported_languages=set(languages),
                platform_requirement=None,  # Available on all platforms
            )
        except Exception:
            self._capabilities[EngineType.TESSERACT] = EngineCapabilities(
                available=False,
                version=None,
                supported_languages=set(),
                platform_requirement=None,
            )

    def _detect_ocrmac(self):
        """Detect ocrmac availability and capabilities."""
        # Platform check
        if platform.system() != "Darwin":
            self._capabilities[EngineType.OCRMAC] = EngineCapabilities(
                available=False,
                version=None,
                supported_languages=set(),
                platform_requirement="darwin",
            )
            return

        try:
            import ocrmac  # noqa: F401

            # ocrmac doesn't expose version or language list directly
            # Use Apple Vision framework supported languages (IETF BCP 47 format)
            # Reference: https://developer.apple.com/documentation/vision/vnrecognizetextrequest
            # Include both bare codes and common regional variants
            languages = {
                # Bare language codes
                "en",
                "fr",
                "de",
                "es",
                "it",
                "pt",
                "ru",
                "ar",
                "ja",
                "ko",
                "th",
                "vi",
                # Common regional variants (IETF BCP 47)
                "en-US",
                "en-GB",
                "en-CA",
                "en-AU",
                "fr-FR",
                "fr-CA",
                "de-DE",
                "de-AT",
                "de-CH",
                "es-ES",
                "es-MX",
                "es-AR",
                "it-IT",
                "pt-PT",
                "pt-BR",
                "ru-RU",
                "ar-SA",
                "ar-AE",
                "ja-JP",
                "ko-KR",
                "th-TH",
                "vi-VN",
                # Chinese with script codes
                "zh-Hans",
                "zh-Hans-CN",
                "zh-Hans-SG",
                "zh-Hant",
                "zh-Hant-TW",
                "zh-Hant-HK",
            }
            self._capabilities[EngineType.OCRMAC] = EngineCapabilities(
                available=True,
                version="0.1.0",  # Package version
                supported_languages=languages,
                platform_requirement="darwin",
            )
        except ImportError:
            self._capabilities[EngineType.OCRMAC] = EngineCapabilities(
                available=False,
                version=None,
                supported_languages=set(),
                platform_requirement="darwin",
            )

    def _detect_easyocr(self):
        """Detect EasyOCR availability and capabilities."""
        try:
            import easyocr  # type: ignore[import-untyped]  # noqa: F401
            import torch  # type: ignore[import-untyped]  # noqa: F401

            # EasyOCR supported languages (80+ languages)
            # Reference: https://github.com/JaidedAI/EasyOCR#supported-languages
            from src.utils.validators import EASYOCR_SUPPORTED_LANGUAGES

            self._capabilities[EngineType.EASYOCR] = EngineCapabilities(
                available=True,
                version="1.7.0",  # EasyOCR package version
                supported_languages=EASYOCR_SUPPORTED_LANGUAGES,
                platform_requirement=None,  # Available on all platforms
            )
        except ImportError:
            self._capabilities[EngineType.EASYOCR] = EngineCapabilities(
                available=False,
                version=None,
                supported_languages=set(),
                platform_requirement=None,
            )

    def is_available(self, engine: EngineType) -> bool:
        """Check if engine is available."""
        return self._capabilities[engine].available

    def get_capabilities(self, engine: EngineType) -> EngineCapabilities:
        """Get cached capabilities for engine."""
        return self._capabilities[engine]

    def validate_platform(self, engine: EngineType) -> tuple[bool, str | None]:
        """
        Validate platform compatibility for engine.

        Returns:
            (is_valid, error_message)
        """
        caps = self._capabilities[engine]
        if caps.platform_requirement is None:
            return (True, None)

        current_platform = platform.system().lower()
        if current_platform != caps.platform_requirement:
            return (
                False,
                f"{engine.value} engine is only available on {caps.platform_requirement} systems. "
                f"Current platform: {current_platform}",
            )
        return (True, None)

    def validate_languages(
        self, engine: EngineType, languages: list[str]
    ) -> tuple[bool, str | None]:
        """
        Validate language codes against engine capabilities.

        Returns:
            (is_valid, error_message)
        """
        caps = self._capabilities[engine]
        if not caps.available:
            return (False, f"{engine.value} engine is not available")

        unsupported = [lang for lang in languages if lang not in caps.supported_languages]

        if unsupported:
            return (
                False,
                f"Unsupported language codes for {engine.value}: {', '.join(unsupported)}. "
                f"Supported: {', '.join(sorted(caps.supported_languages))}",
            )

        return (True, None)
