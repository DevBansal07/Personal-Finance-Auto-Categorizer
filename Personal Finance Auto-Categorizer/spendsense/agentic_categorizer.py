"""
Agentic transaction categorization engine for SpendSense.

Leverages Google Gemini via the google-genai SDK to classify unmatched
transactions using structured output and generates reusable keyword rules.
"""

import json
import os
from pathlib import Path
from pydantic import BaseModel, Field

from spendsense.logger import get_logger

logger = get_logger("agentic_categorizer")


class CategorizationResult(BaseModel):
    """Structured result of a single transaction categorization."""

    description: str = Field(
        description="The exact description of the transaction being categorized."
    )
    category: str = Field(
        description="The matched category (must be one of the existing categories)."
    )
    keyword: str = Field(
        description=(
            "A clean, lowercase keyword/pattern to add to this category to match "
            "similar merchants in the future (e.g., if description is "
            "'uber trip san fran', the keyword should be 'uber')."
        )
    )


class AgenticCategorizerResponse(BaseModel):
    """Wrapper for the list of categorization results."""

    categorizations: list[CategorizationResult]


def run_agentic_categorization(
    uncategorized_descriptions: list[str],
    categories: list[str],
    config_path: str,
) -> dict[str, tuple[str, str]]:
    """Use Gemini to categorize unmatched transactions and suggest keyword rules.

    Args:
        uncategorized_descriptions: List of unique cleaned descriptions.
        categories: List of valid categories.
        config_path: Path to the categories JSON file.

    Returns:
        A dictionary mapping description -> (category, keyword).
    """
    # ── Check for API key ─────────────────────────────────────────────
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY not found in environment. Skipping agentic categorization.")
        return {}

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        logger.warning(
            "google-genai package is not installed. Skipping agentic categorization. "
            "Please run: pip install google-genai"
        )
        return {}

    logger.info("Initializing Gemini GenAI client...")
    try:
        # Initialize client with GEMINI_API_KEY from environment
        client = genai.Client()
    except Exception as exc:
        logger.error("Failed to initialize Gemini Client: %s", exc)
        return {}

    categories_str = ", ".join(categories)
    prompt = f"""You are a personal finance assistant.
We have some raw bank statement transaction descriptions that could not be categorized by our keyword rules.
Your task is to:
1. Map each transaction description to one of the following existing categories: {categories_str}
   Choose the category that fits best.
2. Propose a clean, lowercase keyword/pattern for each transaction that we can save to our rules file.
   The keyword should be the core merchant name, stripped of store numbers, location info, dates, and reference IDs, so it can match future transactions (e.g., if description is "uber trip san fran", the keyword should be "uber").
   Ensure the keyword is specific enough to match this merchant, but general enough to match similar transaction names. Do not use extremely generic keywords that could clash with other categories (e.g. do not use 'corp' or 'ltd').

Transactions to categorize:
{chr(10).join(f"- {desc}" for desc in uncategorized_descriptions)}
"""

    logger.info(
        "Requesting Gemini (gemini-2.5-flash) to categorize %d transaction(s)...",
        len(uncategorized_descriptions),
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AgenticCategorizerResponse,
                temperature=0.1,
            ),
        )

        if not response.text:
            logger.error("Gemini returned an empty response.")
            return {}

        # Parse the structured response
        data = json.loads(response.text)
        results: dict[str, tuple[str, str]] = {}

        for item in data.get("categorizations", []):
            desc = item.get("description")
            cat = item.get("category")
            kw = item.get("keyword", "").strip().lower()

            if not desc or not cat or not kw:
                continue

            if cat in categories:
                results[desc] = (cat, kw)
            else:
                logger.warning(
                    "Suggested category '%s' for description '%s' is invalid. "
                    "Must be one of: %s",
                    cat, desc, categories_str,
                )

        return results

    except Exception as exc:
        logger.error("Gemini API call or response parsing failed: %s", exc)
        return {}


def update_rules_file(config_path: str, new_rules: list[tuple[str, str]]) -> None:
    """Update config/categories.json with newly generated keyword rules.

    Args:
        config_path: Path to the categories.json file.
        new_rules: List of (category, keyword) tuples.
    """
    path = Path(config_path)
    if not path.exists():
        logger.error("Categories config file not found at '%s'", config_path)
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)

        if "categories" not in config:
            logger.error("Invalid categories config schema: missing 'categories' key.")
            return

        categories = config["categories"]
        updated = False

        for category, keyword in new_rules:
            if category in categories:
                # Avoid duplicates
                if keyword not in categories[category]:
                    categories[category].append(keyword)
                    updated = True
                    logger.info("Added learned rule: '%s' -> Category '%s'", keyword, category)
            else:
                logger.warning(
                    "Skipping rule update: Category '%s' does not exist in config.",
                    category,
                )

        if updated:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info("Successfully updated categories configuration at '%s'", config_path)

    except Exception as exc:
        logger.error("Failed to update categories config file: %s", exc)
