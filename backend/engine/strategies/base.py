"""Strategy ABC and shared result types."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from ..citations import Citation
from ..inputs import DonorInputs
from ..regimes.base import StateRegime
from ..tax_context import TaxContext, ZERO, round_cents


@dataclass
class YearlyRow:
    """One row of the year-by-year projection (used to feed the accumulation chart)."""
    year_index: int             # 0 = year of first contribution
    child_age: int
    contributions_to_date: Decimal
    pretax_balance: Decimal
    annual_tax_drag: Decimal    # tax paid during the year on dividends/realized gains
    cumulative_tax_drag: Decimal

    def to_dict(self) -> dict:
        return {
            "year_index": self.year_index,
            "child_age": self.child_age,
            "contributions_to_date": str(self.contributions_to_date),
            "pretax_balance": str(self.pretax_balance),
            "annual_tax_drag": str(self.annual_tax_drag),
            "cumulative_tax_drag": str(self.cumulative_tax_drag),
        }


@dataclass
class TaxExplanation:
    """A line item in the taxes-paid breakdown plus a why-it-was-paid rationale.

    The wire shape includes the human-readable amount string so the UI can
    show the figure inline with the explanation without having to re-look up
    the breakdown dict.
    """
    line: str                # one of: income, capital_gains, gift, estate, gst, state_income, state_estate
    label: str               # display label, e.g. "Federal estate tax"
    amount: Decimal
    rationale: str           # why this tax was paid, in plain language

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "label": self.label,
            "amount": str(self.amount),
            "rationale": self.rationale,
        }


@dataclass
class StrategyResult:
    strategy_name: str
    contribution_total: Decimal
    pretax_terminal_value: Decimal
    taxes_paid_breakdown: dict[str, Decimal]   # keys: income, capital_gains, gift, estate, gst, state_income, state_estate
    after_tax_wealth_to_recipient: Decimal
    effective_tax_rate: Decimal
    year_by_year_projection: list[YearlyRow]
    citations: list[Citation]
    assumptions: list[str]
    warnings: list[str] = field(default_factory=list)
    is_available: bool = True   # False for strategies blocked by input constraints (e.g., Roth IRA with no earned income)
    unavailable_reason: Optional[str] = None
    tax_explanations: list["TaxExplanation"] = field(default_factory=list)

    def to_dict(self) -> dict:
        seen: set[tuple[str, str]] = set()
        unique_citations: list[Citation] = []
        for c in self.citations:
            key = (c.section, c.description)
            if key in seen:
                continue
            seen.add(key)
            unique_citations.append(c)
        return {
            "strategy_name": self.strategy_name,
            "is_available": self.is_available,
            "unavailable_reason": self.unavailable_reason,
            "contribution_total": str(self.contribution_total),
            "pretax_terminal_value": str(self.pretax_terminal_value),
            "taxes_paid_breakdown": {k: str(v) for k, v in self.taxes_paid_breakdown.items()},
            "after_tax_wealth_to_recipient": str(self.after_tax_wealth_to_recipient),
            "effective_tax_rate": str(self.effective_tax_rate),
            "year_by_year_projection": [r.to_dict() for r in self.year_by_year_projection],
            "citations": [c.to_dict() for c in unique_citations],
            "assumptions": self.assumptions,
            "warnings": self.warnings,
            "tax_explanations": [t.to_dict() for t in self.tax_explanations],
        }


class Strategy(ABC):
    """All six strategies inherit from this and implement `evaluate`."""

    name: str

    @abstractmethod
    def evaluate(
        self,
        ctx: TaxContext,
        regime: StateRegime,
        inputs: DonorInputs,
    ) -> StrategyResult: ...

    def _empty_breakdown(self) -> dict[str, Decimal]:
        return {
            "income": ZERO,
            "capital_gains": ZERO,
            "gift": ZERO,
            "estate": ZERO,
            "gst": ZERO,
            "state_income": ZERO,
            "state_estate": ZERO,
        }

    def _effective_tax_rate(
        self,
        breakdown: dict[str, Decimal],
        contribution_total: Decimal,
        pretax_terminal_value: Decimal,
    ) -> Decimal:
        total_tax = sum(breakdown.values())
        # ETR = total tax / total tax-base (pretax terminal + cumulative income drag).
        # Using pretax terminal as the denominator gives a clean comparison metric.
        if pretax_terminal_value <= ZERO:
            return ZERO
        return round_cents((total_tax / pretax_terminal_value) * Decimal("100")) / Decimal("100")
