"""
Rule-based transaction categorization engine for SpendSense.

Reads a configurable JSON file mapping keywords to budget categories,
cleans messy merchant descriptions with regex, and assigns each
transaction to the best-matching category.
"""

import json
import re
from pathlib import Path

from spendsense.exceptions import ConfigError
from spendsense.logger import get_logger

logger = get_logger("categorizer")

# ── Regex patterns for cleaning raw merchant descriptions ───────────
# Matches trailing transaction codes, reference numbers, merchant IDs
_PATTERNS_TO_STRIP = [
    r"\b[A-Z]{2,4}\s*\*\s*",            # Prefixes like "POS *", "SQ *", "TST *"
    r"#\d+",                              # Reference numbers: #123456
    r"\b\d{6,}\b",                        # Long digit sequences (transaction IDs)
    r"\b\d{3,5}\b",                       # Medium digit sequences (store numbers)
    r"\b(POS|ACH|DEBIT|CREDIT|PURCHASE|WITHDRAWAL|PAYMENT)\b",  # Transaction type labels
    r"\b[A-Z]{2}\s?\d{2,5}\b",           # Codes like CA 94105 (zip), TX 75001
    r"[^a-zA-Z0-9\s&\-]",               # Special characters except & and -
    r"\s{2,}",                            # Collapse multiple spaces
]


def load_rules(config_path: str) -> tuple[dict[str, str], str]:
    """Load and validate the category rules configuration.

    Builds an inverted lookup table mapping each keyword to its category.

    Args:
        config_path: Path to the categories JSON file.

    Returns:
        A tuple of (rules_dict, default_category) where rules_dict maps
        lowercase keywords to their category names.

    Raises:
        ConfigError: If the file is missing, malformed, or has invalid schema.
    """
    path = Path(config_path)

    if not path.exists():
        raise ConfigError(config_path, "Configuration file not found.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as exc:
        raise ConfigError(config_path, f"Invalid JSON: {exc}") from exc

    # ── Schema validation ────────────────────────────────────────────
    if "categories" not in config:
        raise ConfigError(config_path, "Missing required key 'categories'.")

    if not isinstance(config["categories"], dict):
        raise ConfigError(config_path, "'categories' must be a JSON object.")

    default_category = config.get("default_category", "Uncategorized")

    # ── Build inverted lookup: keyword → category ────────────────────
    rules: dict[str, str] = {}
    total_keywords = 0

    for category, keywords in config["categories"].items():
        if not isinstance(keywords, list):
            raise ConfigError(
                config_path,
                f"Keywords for category '{category}' must be a list, "
                f"got {type(keywords).__name__}.",
            )
        for keyword in keywords:
            normalized = keyword.strip().lower()
            if normalized:
                rules[normalized] = category
                total_keywords += 1

    logger.info(
        "Loaded %d keywords across %d categories from '%s'",
        total_keywords,
        len(config["categories"]),
        config_path,
    )

    return rules, default_category


def clean_description(raw: str) -> str:
    """Clean a raw merchant description for keyword matching.

    Strips transaction codes, merchant IDs, special characters,
    and normalizes whitespace.

    Args:
        raw: Raw transaction description from the bank statement.
            Example: "POS DEBIT UBER *TRIP 8374829 SAN FRAN CA 94105"

    Returns:
        Cleaned, lowercased description.
            Example: "uber trip san fran"
    """
    cleaned = raw.lower()

    for pattern in _PATTERNS_TO_STRIP:
        cleaned = re.sub(pattern, " ", cleaned, flags=re.IGNORECASE)

    # Final whitespace normalization
    cleaned = cleaned.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned


def categorize_transaction(
    description: str, rules: dict[str, str], default: str
) -> str:
    """Categorize a single transaction by matching keywords.

    Performs substring matching against the cleaned description,
    checking longer keywords first for more precise matches.

    Args:
        description: Cleaned transaction description.
        rules: Inverted keyword → category lookup.
        default: Default category for unrecognized transactions.

    Returns:
        The matched category name, or the default if no match found.
    """
    # Sort keywords by length descending — longer matches are more specific
    for keyword in sorted(rules.keys(), key=len, reverse=True):
        if keyword in description:
            return rules[keyword]

    return default


def categorize_dataframe(
    df,
    rules: dict[str, str],
    default: str = "Uncategorized",
    agentic: bool = False,
    config_path: str | None = None,
):
    """Apply categorization to all transactions in the DataFrame.

    Adds a 'category' column with the matched budget category for each row.
    If agentic=True and config_path is provided, uses Gemini to categorize
    unmatched rows and saves them as permanent keyword rules.

    Args:
        df: DataFrame with a 'description' column.
        rules: Inverted keyword → category lookup from load_rules().
        default: Default category for unmatched transactions.
        agentic: Whether to use agentic fallback with Gemini.
        config_path: Path to categories.json file to update with learned rules.

    Returns:
        DataFrame with the new 'category' column added.
    """
    import pandas as pd

    logger.info("Categorizing %d transactions...", len(df))

    # Clean descriptions and categorize
    cleaned = df["description"].apply(clean_description)
    df = df.copy()
    df["category"] = cleaned.apply(
        lambda desc: categorize_transaction(desc, rules, default)
    )

    # ── Agentic Fallback ─────────────────────────────────────────────
    uncategorized_mask = df["category"] == default
    uncategorized_count = uncategorized_mask.sum()

    if agentic and uncategorized_count > 0 and config_path:
        logger.info("Agentic fallback enabled. Scanning %d unmatched rows...", uncategorized_count)
        
        # Get unique cleaned descriptions for unmatched rows
        unique_uncat = cleaned[uncategorized_mask].unique().tolist()
        
        # List of valid categories from current rules
        categories = list(set(rules.values()))
        
        from spendsense.agentic_categorizer import run_agentic_categorization, update_rules_file
        
        suggestions = run_agentic_categorization(unique_uncat, categories, config_path)
        
        if suggestions:
            new_rules = []
            for desc, (category, keyword) in suggestions.items():
                matches = (cleaned == desc) & (df["category"] == default)
                df.loc[matches, "category"] = category
                new_rules.append((category, keyword))
                
            # Persist learned rules back to JSON config
            update_rules_file(config_path, new_rules)
            
            logger.info("Agentic phase complete. Applied %d categorization suggestions.", len(suggestions))
        else:
            logger.info("No agentic updates were applied.")

    # ── Log summary statistics ───────────────────────────────────────
    category_counts = df["category"].value_counts()
    uncategorized_count = category_counts.get(default, 0)
    categorized_count = len(df) - uncategorized_count

    logger.info(
        "Categorization complete: %d categorized, %d uncategorized",
        categorized_count,
        uncategorized_count,
    )

    if uncategorized_count > 0:
        uncategorized_items = df.loc[
            df["category"] == default, "description"
        ].tolist()
        logger.warning(
            "Uncategorized transactions (%d): %s",
            uncategorized_count,
            uncategorized_items[:10],  # Log first 10 at most
        )

    # Log per-category breakdown
    for category, count in category_counts.items():
        if category != default:
            logger.info("  %-20s %d transactions", category, count)

    return df
