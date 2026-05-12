"""Wealth Transfer Strategy Comparison Engine.

A deterministic, citation-traced tax calculation engine for comparing six wealth
transfer vehicles across three U.S. state regimes (NY, IL, TX) for tax year 2025.

All monetary calculations use `decimal.Decimal` for byte-identical reproducibility.
Every numeric output carries a `citations: list[Citation]` payload tracing it back
to the Internal Revenue Code, Treasury Regulations, or state statute.
"""

__version__ = "0.1.0"
