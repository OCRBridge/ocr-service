"""Exception hierarchy for OCR Bridge."""


class OCRBridgeError(Exception):
    """Base exception for all OCR Bridge errors.

    All custom exceptions in the OCR Bridge ecosystem should inherit from this
    base exception to allow for broad exception handling when needed.
    """

    pass


class OCRProcessingError(OCRBridgeError):
    """Raised when OCR processing fails.

    This exception is raised when the OCR engine encounters an error during
    document processing, such as:
    - Engine binary not found or not executable
    - Engine crashed or returned non-zero exit code
    - Output format is invalid or cannot be parsed
    - Timeout during processing
    """

    pass


class UnsupportedFormatError(OCRBridgeError):
    """Raised when file format is not supported by the engine.

    This exception is raised when attempting to process a file with an extension
    not in the engine's supported_formats set.
    """

    pass


class EngineNotAvailableError(OCRBridgeError):
    """Raised when requested engine is not installed or available.

    This exception is raised when:
    - Engine package is not installed
    - Engine entry point cannot be loaded
    - Engine dependencies are missing
    - Engine is platform-specific and current platform doesn't match
    """

    pass


class InvalidParametersError(OCRBridgeError):
    """Raised when engine parameters are invalid.

    This exception is raised when parameter validation fails, such as:
    - Invalid parameter values (out of range, wrong type)
    - Required parameters missing
    - Unknown parameters provided
    - Parameter combination is invalid
    """

    pass
