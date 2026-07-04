# Changelog

All notable changes to SpendSense will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-30

### Added

- **Data Ingestion** — CSV and Excel (.xlsx) bank statement loading with auto-detection.
- **Column Auto-Matching** — Case-insensitive matching against 20+ known column aliases (Date, Description, Amount and variants like Payee, Merchant, Narration, etc.).
- **Data Validation** — Custom exception hierarchy (`FileFormatError`, `MissingColumnError`, `DataValidationError`, `EmptyDatasetError`) with actionable error messages.
- **Currency Stripping** — Automatic removal of `$`, `£`, `€`, `₹`, commas from amount fields.
- **Rule-Based Categorizer** — Configurable JSON keyword-to-category engine with 165 keywords across 13 budget categories.
- **Regex Cleaning** — 7 regex patterns strip POS codes, merchant IDs, transaction numbers, and zip codes from messy bank descriptions.
- **Length-Sorted Matching** — Keywords matched longest-first to prevent short keywords from shadowing more specific ones.
- **Analytics Engine** — Computes total spend, daily average, spend by category, top 5 transactions, uncategorized percentage, and date range.
- **Interactive HTML Reports** — Plotly-powered dark-themed dashboard with donut chart, horizontal bar chart, KPI stat cards, progress-bar category breakdown, and top transactions panel.
- **Matplotlib Fallback** — Automatic fallback to static PNG-in-HTML report if Plotly is not installed.
- **Structured Logging** — Python `logging` module with `[timestamp] [LEVEL] module: message` format, UTF-8 console output.
- **CLI Interface** — `argparse`-based with `--file`, `--config`, and `--output` flags.
- **Sample Data** — 51-row synthetic bank statement with realistic messy merchant descriptions for demo/testing.

[1.0.0]: https://github.com/yourusername/spendsense/releases/tag/v1.0.0
