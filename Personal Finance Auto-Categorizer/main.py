"""
SpendSense — CLI Entry Point.

Orchestrates the full pipeline: ingest → categorize → report.
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from spendsense.exceptions import SpendSenseError
from spendsense.logger import get_logger, setup_logging


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed namespace with file, config, and output attributes.
    """
    parser = argparse.ArgumentParser(
        prog="spendsense",
        description=(
            "SpendSense — Personal Finance Auto-Categorizer.\n"
            "Ingest raw bank statements, auto-categorize transactions, "
            "and generate interactive spending reports."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python main.py --file bank_statement.csv\n"
            "  python main.py --file statement.xlsx --config my_rules.json\n"
            "  python main.py --file data.csv --output reports/\n"
        ),
    )

    parser.add_argument(
        "--file", "-f",
        required=True,
        help="Path to the bank statement file (.csv or .xlsx).",
    )
    parser.add_argument(
        "--config", "-c",
        default="config/categories.json",
        help="Path to the category rules JSON file (default: config/categories.json).",
    )
    parser.add_argument(
        "--output", "-o",
        default="output",
        help="Output directory for generated reports (default: output/).",
    )
    parser.add_argument(
        "--agentic",
        action="store_true",
        help="Force agentic mode using Gemini LLM to categorize unmatched transactions.",
    )
    parser.add_argument(
        "--no-agentic",
        action="store_true",
        help="Disable agentic mode even if GEMINI_API_KEY is present.",
    )

    return parser.parse_args(argv)


def run_pipeline(filepath: str, config_path: str, output_dir: str, agentic: bool = False) -> None:
    """Execute the full SpendSense pipeline.

    Steps:
        1. Load and validate the bank statement.
        2. Load categorization rules.
        3. Categorize all transactions.
        4. Compute analytics.
        5. Generate the visual report.

    Args:
        filepath: Path to the bank statement file.
        config_path: Path to the categories JSON config.
        output_dir: Directory for output reports.
        agentic: Whether to run agentic categorization for unmatched rows.
    """
    from spendsense.categorizer import categorize_dataframe, load_rules
    from spendsense.data_loader import load_statement
    from spendsense.reporter import compute_analytics, generate_report

    logger = get_logger("pipeline")

    # ── Step 1: Ingest ───────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("PHASE 1: Data Ingestion & Validation")
    logger.info("=" * 60)
    df = load_statement(filepath)

    # ── Step 2: Load rules ───────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("PHASE 2: Rule-Based Categorization")
    logger.info("=" * 60)
    rules, default_category = load_rules(config_path)

    # ── Step 3: Categorize ───────────────────────────────────────────
    df = categorize_dataframe(
        df, rules, default_category, agentic=agentic, config_path=config_path
    )

    # ── Step 4: Analytics ────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("PHASE 3: Analytics & Reporting")
    logger.info("=" * 60)
    analytics = compute_analytics(df)

    # ── Step 5: Report ───────────────────────────────────────────────
    report_path = generate_report(analytics, output_dir)

    # ── Final Summary ────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 60)
    logger.info("Total Spend:       $%s", f"{analytics['total_spend']:,.2f}")
    logger.info("Transactions:      %d", analytics["transaction_count"])
    logger.info("Categories:        %d", len(analytics["spend_by_category"]))
    logger.info("Uncategorized:     %d (%.1f%%)", analytics["uncategorized_count"], analytics["uncategorized_pct"])
    logger.info("Daily Average:     $%s", f"{analytics['avg_daily_spend']:,.2f}")
    logger.info("Date Range:        %s to %s", *analytics["date_range"])
    logger.info("Report:            %s", report_path)
    logger.info("=" * 60)


def main() -> None:
    """CLI entry point with top-level error handling."""
    load_dotenv()
    setup_logging()
    logger = get_logger("main")

    args = parse_args()

    # Resolve relative paths against the script's directory
    script_dir = Path(__file__).resolve().parent
    filepath = str(Path(args.file).resolve() if Path(args.file).is_absolute() else script_dir / args.file)
    config_path = str(Path(args.config).resolve() if Path(args.config).is_absolute() else script_dir / args.config)
    output_dir = str(Path(args.output).resolve() if Path(args.output).is_absolute() else script_dir / args.output)

    # Determine if agentic mode should be enabled
    has_api_key = bool(os.environ.get("GEMINI_API_KEY"))
    agentic_enabled = False
    
    if args.agentic:
        agentic_enabled = True
    elif has_api_key and not args.no_agentic:
        agentic_enabled = True

    if agentic_enabled and not has_api_key:
        logger.warning(
            "⚠️ Agentic mode is enabled, but GEMINI_API_KEY environment variable is not set. "
            "Pipeline will fall back to rule-only mode."
        )

    logger.info("SpendSense v1.0.0 — Personal Finance Auto-Categorizer")
    logger.info("Input:  %s", filepath)
    logger.info("Config: %s", config_path)
    logger.info("Output: %s", output_dir)
    logger.info("Mode:   %s", "Agentic (Gemini fallback)" if agentic_enabled else "Rule-Only")
    logger.info("")

    try:
        run_pipeline(filepath, config_path, output_dir, agentic=agentic_enabled)
    except SpendSenseError as exc:
        logger.error("❌ %s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user.")
        sys.exit(130)
    except Exception as exc:
        logger.exception("❌ Unexpected error: %s", exc)
        sys.exit(2)


if __name__ == "__main__":
    main()
