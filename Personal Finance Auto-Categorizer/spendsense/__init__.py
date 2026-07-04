"""
SpendSense — Personal Finance Auto-Categorizer.

A production-grade tool for ingesting raw bank statements,
auto-categorizing transactions, and generating interactive spending reports.
"""

__version__ = "1.0.0"
__author__ = "SpendSense"

from spendsense.data_loader import load_statement
from spendsense.categorizer import categorize_dataframe, load_rules
from spendsense.reporter import compute_analytics, generate_report

__all__ = [
    "load_statement",
    "load_rules",
    "categorize_dataframe",
    "compute_analytics",
    "generate_report",
]
