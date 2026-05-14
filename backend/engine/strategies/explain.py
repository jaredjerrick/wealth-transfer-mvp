"""Tax-explanation helpers — turns a `taxes_paid_breakdown` dict into a list
of `TaxExplanation` rows with plain-language rationales.

The strategy modules call `build_tax_explanations(...)` near the end of their
`evaluate` to attach a "why this was paid (and how much)" narrative to each
non-zero line in the breakdown. The UI renders these in the comparison table
and the PDF Strategy Brief.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from ..tax_context import D, ZERO
from .base import TaxExplanation


# Display labels for each canonical line in `taxes_paid_breakdown`.
LINE_LABELS = {
    "income": "Federal income tax",
    "capital_gains": "Federal capital-gains / dividend tax",
    "gift": "Federal gift tax",
    "estate": "Federal estate tax",
    "gst": "Generation-skipping transfer (GST) tax",
    "state_income": "State income tax",
    "state_estate": "State estate tax",
}


def build_tax_explanations(
    breakdown: dict[str, Decimal],
    rationales: dict[str, str],
) -> list[TaxExplanation]:
    """For each non-zero line in `breakdown`, emit a TaxExplanation.

    Args:
        breakdown: the StrategyResult.taxes_paid_breakdown dict.
        rationales: a strategy-supplied dict mapping line key → plain-English
            "why this was paid" string. Lines without a rationale fall back to
            a generic per-line note. Negative values (state-income benefits
            like a 529 deduction credit) are surfaced too — the rationale
            should mention that the line represents a saving.
    """
    rows: list[TaxExplanation] = []
    for line, amount in breakdown.items():
        amt = D(amount)
        if amt == ZERO:
            continue
        label = LINE_LABELS.get(line, line.replace("_", " ").title())
        rationale = rationales.get(line) or _fallback_rationale(line)
        rows.append(TaxExplanation(line=line, label=label, amount=amt, rationale=rationale))
    return rows


def _fallback_rationale(line: str) -> str:
    return {
        "income": "Ordinary income tax assessed on taxable distributions or unearned income during accumulation.",
        "capital_gains": "Preferential-rate tax on qualified dividends and realized long-term capital gains.",
        "gift": "Gift tax due to the extent contributions exceeded the annual exclusion and the donor's remaining lifetime exemption.",
        "estate": "Federal estate tax on the slice of the taxable estate attributable to this strategy's terminal value.",
        "gst": "GST tax applied because the recipient is a skip person (e.g., grandchild) and remaining §2631 exemption was insufficient.",
        "state_income": "State income tax assessed under the donor's state regime (or the deductible benefit, if negative).",
        "state_estate": "State estate tax on the slice attributable to this strategy's terminal value.",
    }.get(line, "Tax assessed under the cited authority.")
