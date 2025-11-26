"Tesseract engine specific utilities."

import functools
import subprocess
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


DEFAULT_TESSERACT_LANGUAGES = {
    "eng",
    "fra",
    "deu",
    "spa",
    "ita",
    "por",
    "rus",
    "ara",
    "chi_sim",
    "jpn",
}


@dataclass
class TesseractConfig:
    """Resolved Tesseract configuration for processing."""

    lang: str  # Never None, defaults to 'eng'
    config_string: str  # CLI config string (e.g., "--psm 6 --oem 1 --dpi 300")


@functools.lru_cache(maxsize=1)
def get_installed_languages() -> set[str]:
    """
    Get list of installed Tesseract language data files.

    Uses subprocess to call 'tesseract --list-langs' and caches the result.
    Fallback to common languages if command fails.

    Returns:
        Set of installed language codes (e.g., {'eng', 'fra', 'deu'})
    """
    try:
        result = subprocess.run(
            ["tesseract", "--list-langs"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            # Parse output, skip header line "List of available languages (N):"
            langs = result.stdout.strip().split("\n")[1:]
            installed = {lang.strip() for lang in langs if lang.strip()}
            installed.update(DEFAULT_TESSERACT_LANGUAGES)

            logger.info(
                "tesseract_languages_detected",
                count=len(installed),
                languages=sorted(installed)[:10],  # Log first 10
            )

            return installed
        else:
            logger.warning(
                "tesseract_list_langs_failed",
                returncode=result.returncode,
                stderr=result.stderr,
            )
            # Fallback to common languages
            return set(DEFAULT_TESSERACT_LANGUAGES)

    except FileNotFoundError:
        logger.error("tesseract_not_found")
        # Fallback to default languages
        return set(DEFAULT_TESSERACT_LANGUAGES)
    except subprocess.TimeoutExpired:
        logger.error("tesseract_list_langs_timeout")
        return set(DEFAULT_TESSERACT_LANGUAGES)
    except Exception as e:
        logger.error("tesseract_list_langs_error", error=str(e))
        return set(DEFAULT_TESSERACT_LANGUAGES)


def build_tesseract_config(
    lang: str | None = None,
    psm: int | None = None,
    oem: int | None = None,
    dpi: int | None = None,
) -> TesseractConfig:
    """
    Build Tesseract configuration from validated parameters.

    Converts optional parameters to resolved config with defaults applied.

    Args:
        lang: Language code(s), defaults to 'eng' if None
        psm: Page segmentation mode (0-13), omitted if None
        oem: OCR engine mode (0-3), omitted if None
        dpi: Image DPI (70-2400), omitted if None

    Returns:
        TesseractConfig with resolved language and config string
    """
    # Default language to English if not specified
    resolved_lang = lang or "eng"

    # Build config string from non-None parameters
    config_parts = []

    if psm is not None:
        config_parts.append(f"--psm {psm}")

    if oem is not None:
        config_parts.append(f"--oem {oem}")

    if dpi is not None:
        config_parts.append(f"--dpi {dpi}")

    config_string = " ".join(config_parts)

    return TesseractConfig(lang=resolved_lang, config_string=config_string)
