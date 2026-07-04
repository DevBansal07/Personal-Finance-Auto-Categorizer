"""
Data ingestion and validation module for SpendSense.

Handles loading bank statements from CSV/Excel files, validating
required columns exist, and coercing data types for downstream processing.
"""

from pathlib import Path

import pandas as pd

from spendsense.exceptions import (
    DataValidationError,
    EmptyDatasetError,
    FileFormatError,
    MissingColumnError,
)
from spendsense.logger import get_logger

logger = get_logger("data_loader")

# ── Column Alias Mappings ───────────────────────────────────────────
# Maps canonical column names to known aliases across various bank formats.
COLUMN_ALIASES: dict[str, list[str]] = {
    "date": ["date", "transaction date", "trans date", "posting date", "value date"],
    "description": [
        "description",
        "payee",
        "merchant",
        "narration",
        "details",
        "transaction description",
        "memo",
        "particulars",
    ],
    "amount": [
        "amount",
        "debit amount",
        "transaction amount",
        "value",
        "debit",
        "withdrawal",
    ],
}

SUPPORTED_EXTENSIONS = {".csv", ".xlsx"}


def load_statement(filepath: str) -> pd.DataFrame:
    """Load, validate, and clean a bank statement file.

    This is the primary public API for data ingestion. It orchestrates
    the full pipeline: load → validate columns → coerce types → clean.

    Args:
        filepath: Path to the bank statement file (.csv or .xlsx).

    Returns:
        A clean, validated DataFrame with canonical columns:
        ['date', 'description', 'amount'].

    Raises:
        FileNotFoundError: If the file does not exist.
        FileFormatError: If the file extension is unsupported.
        MissingColumnError: If required columns are absent.
        DataValidationError: If critical data types cannot be coerced.
        EmptyDatasetError: If no valid rows remain after cleaning.
    """
    path = Path(filepath)

    # ── File existence check ────────────────────────────────────────
    if not path.exists():
        logger.error("File not found: %s", filepath)
        raise FileNotFoundError(f"Statement file not found: '{filepath}'")

    # ── Extension check ─────────────────────────────────────────────
    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        logger.error("Unsupported file format: %s", extension)
        raise FileFormatError(filepath, extension)

    # ── Read file ────────────────────────────────────────────────────
    df = _read_file(path, extension)
    logger.info("Raw file loaded: %d rows, %d columns", len(df), len(df.columns))

    # ── Validate & rename columns ────────────────────────────────────
    df = _validate_and_rename_columns(df)

    # ── Coerce data types & clean ────────────────────────────────────
    df = _clean_and_coerce(df)

    logger.info(
        "Data ingestion complete: %d valid transactions loaded", len(df)
    )
    return df


def _read_file(path: Path, extension: str) -> pd.DataFrame:
    """Read a file into a DataFrame based on its extension.

    Args:
        path: Resolved file path.
        extension: Lowercase file extension (e.g., '.csv').

    Returns:
        Raw DataFrame as read from the file.

    Raises:
        FileFormatError: If reading fails due to format issues.
    """
    try:
        if extension == ".csv":
            return pd.read_csv(path, dtype=str, keep_default_na=False)
        else:  # .xlsx
            return pd.read_excel(
                path, dtype=str, keep_default_na=False, engine="openpyxl"
            )
    except Exception as exc:
        logger.error("Failed to read file '%s': %s", path, exc)
        raise FileFormatError(str(path), extension) from exc


def _validate_and_rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Validate that required columns exist and rename to canonical names.

    Uses case-insensitive, whitespace-stripped matching against
    known column aliases.

    Args:
        df: Raw DataFrame with original column names.

    Returns:
        DataFrame with columns renamed to canonical names.

    Raises:
        MissingColumnError: If any required canonical column cannot be matched.
    """
    # Normalize original column names for matching
    original_columns = list(df.columns)
    normalized_map: dict[str, str] = {}
    for col in original_columns:
        normalized_map[col.strip().lower()] = col

    rename_map: dict[str, str] = {}
    missing: list[str] = []

    for canonical, aliases in COLUMN_ALIASES.items():
        matched = False
        for alias in aliases:
            if alias in normalized_map:
                rename_map[normalized_map[alias]] = canonical
                matched = True
                break
        if not matched:
            missing.append(canonical)

    if missing:
        logger.error(
            "Missing required columns: %s (available: %s)", missing, original_columns
        )
        raise MissingColumnError(missing, original_columns)

    df = df.rename(columns=rename_map)
    logger.info(
        "Column mapping applied: %s",
        {v: k for k, v in rename_map.items()},
    )
    return df


def _clean_and_coerce(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce data types and clean the validated DataFrame.

    - Parses 'date' to datetime64.
    - Coerces 'amount' to float64 (absolute values for expense analysis).
    - Strips whitespace from 'description'.
    - Drops rows with NaN in critical columns.

    Args:
        df: DataFrame with canonical column names.

    Returns:
        Cleaned, type-safe DataFrame.

    Raises:
        DataValidationError: If date or amount columns are entirely unparseable.
        EmptyDatasetError: If no valid rows remain after cleaning.
    """
    initial_count = len(df)

    # ── Date coercion ────────────────────────────────────────────────
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=False)
    date_nulls = df["date"].isna().sum()
    if date_nulls == initial_count:
        raise DataValidationError(
            "date", "All date values are unparseable. Check the date format."
        )
    if date_nulls > 0:
        logger.warning(
            "Dropped %d row(s) with unparseable dates", date_nulls
        )

    # ── Amount coercion ──────────────────────────────────────────────
    # Strip currency symbols, commas, and whitespace before conversion
    df["amount"] = (
        df["amount"]
        .astype(str)
        .str.replace(r"[,$£€₹\s]", "", regex=True)
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    amount_nulls = df["amount"].isna().sum()
    if amount_nulls == initial_count:
        raise DataValidationError(
            "amount", "All amount values are non-numeric. Check the amount column."
        )
    if amount_nulls > 0:
        logger.warning(
            "Dropped %d row(s) with non-numeric amounts", amount_nulls
        )

    # ── Convert to absolute values (expenses as positive) ────────────
    df["amount"] = df["amount"].abs()

    # ── Description cleanup ──────────────────────────────────────────
    df["description"] = df["description"].astype(str).str.strip()

    # ── Drop rows with any critical NaN ──────────────────────────────
    df = df.dropna(subset=["date", "description", "amount"]).reset_index(drop=True)

    dropped = initial_count - len(df)
    if dropped > 0:
        logger.warning(
            "Total rows dropped during cleaning: %d / %d", dropped, initial_count
        )

    if len(df) == 0:
        raise EmptyDatasetError(
            f"All {initial_count} rows were invalid after cleaning."
        )

    # ── Keep only canonical columns + any extras ─────────────────────
    canonical = ["date", "description", "amount"]
    extra_cols = [c for c in df.columns if c not in canonical]
    df = df[canonical + extra_cols]

    return df
