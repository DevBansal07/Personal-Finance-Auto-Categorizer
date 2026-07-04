"""
Custom exception hierarchy for SpendSense.

All application-specific errors inherit from SpendSenseError,
enabling callers to catch a single base class for graceful handling.
"""


class SpendSenseError(Exception):
    """Base exception for all SpendSense application errors."""


class FileFormatError(SpendSenseError):
    """Raised when the input file has an unsupported format.

    Supported formats: .csv, .xlsx
    """

    def __init__(self, filepath: str, extension: str) -> None:
        self.filepath = filepath
        self.extension = extension
        super().__init__(
            f"Unsupported file format '{extension}' for file '{filepath}'. "
            f"Supported formats: .csv, .xlsx"
        )


class MissingColumnError(SpendSenseError):
    """Raised when required columns are absent from the uploaded statement."""

    def __init__(self, missing: list[str], available: list[str]) -> None:
        self.missing = missing
        self.available = available
        super().__init__(
            f"Missing required column(s): {missing}. "
            f"Available columns: {available}. "
            f"Please ensure your statement contains: Date, Description/Payee, Amount."
        )


class DataValidationError(SpendSenseError):
    """Raised when data types are corrupt or cannot be coerced."""

    def __init__(self, column: str, detail: str) -> None:
        self.column = column
        self.detail = detail
        super().__init__(
            f"Data validation failed for column '{column}': {detail}"
        )


class EmptyDatasetError(SpendSenseError):
    """Raised when the file loads but contains zero usable rows."""

    def __init__(self, reason: str = "No valid rows remain after cleaning.") -> None:
        self.reason = reason
        super().__init__(f"Empty dataset: {reason}")


class ConfigError(SpendSenseError):
    """Raised when the category configuration file is invalid or missing."""

    def __init__(self, config_path: str, detail: str) -> None:
        self.config_path = config_path
        self.detail = detail
        super().__init__(
            f"Configuration error in '{config_path}': {detail}"
        )
