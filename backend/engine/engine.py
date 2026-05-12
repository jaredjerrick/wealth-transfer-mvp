"""Top-level orchestrator. Runs all six strategies for the requested state."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from .inputs import DonorInputs
from .regimes import regime_for
from .strategies import ALL_STRATEGIES, StrategyResult
from .tax_context import TaxContext, load_rules


@dataclass
class CompareResult:
    inputs_echo: dict
    rules_version: dict
    results: list[StrategyResult]
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "inputs": self.inputs_echo,
            "rules_version": self.rules_version,
            "results": [r.to_dict() for r in self.results],
            "recommendations": self.recommendations,
        }


def _build_recommendations(inputs: DonorInputs, results: list[StrategyResult]) -> list[str]:
    """Rules-based suggestions surfaced on the dashboard. Not LLM-generated."""
    recs: list[str] = []

    # Estate-tax exposure
    if inputs.donor_net_worth > Decimal("7000000") and inputs.state.value == "NY":
        recs.append(
            "Donor's net worth is near or above the NY $7.16M estate exemption — "
            "lifetime gifting strategies (annual exclusion + 5-year 529 election) "
            "may reduce or eliminate the NY estate cliff exposure."
        )
    if inputs.donor_net_worth > Decimal("4000000") and inputs.state.value == "IL":
        recs.append(
            "Donor exceeds the IL $4M estate exemption (not portable, not indexed). "
            "Lifetime gifting and federal-state exemption mismatch warrant attention."
        )
    if inputs.donor_net_worth > Decimal("13990000"):
        recs.append(
            "Donor's net worth exceeds the federal §2010 basic exclusion ($13.99M, 2025). "
            "Federal estate tax exposure is material; consider lifetime gifting and §2031 "
            "valuation planning."
        )

    # UTMA control transfer
    age_of_majority = 21
    if inputs.child_age + inputs.investment_horizon_years > age_of_majority:
        years_to_majority = max(0, age_of_majority - inputs.child_age)
        recs.append(
            f"Child reaches state UTMA age of majority (21) at year {years_to_majority}. "
            f"UTMA control transfers to the beneficiary at that point — model this in "
            f"the UGMA/UTMA strategy and consider trust alternatives for longer-horizon control."
        )

    # Roth blocking
    if inputs.child_earned_income <= Decimal("0"):
        recs.append(
            "Roth IRA path is blocked: child has no earned income (IRC §219(b), §408A(c)(2)). "
            "If the child works (W-2 or self-employment), the Roth path becomes the most "
            "tax-efficient long-horizon vehicle on a per-dollar basis."
        )

    # Community-property edge
    if inputs.state.value == "TX" and inputs.spouse_present:
        recs.append(
            "Married Texas donors receive a §1014(b)(6) double step-up on community "
            "property at the first spouse's death — a meaningful capital-gains-tax saving "
            "vs. equivalent New York or Illinois married donors."
        )

    return recs


def compare_strategies(
    inputs: DonorInputs,
    rules: Optional[dict] = None,
) -> CompareResult:
    """Run all six strategy modules and return the comparison."""
    rules = rules if rules is not None else load_rules()
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(inputs.state, rules)

    results = []
    for strategy_cls in ALL_STRATEGIES:
        strategy = strategy_cls()
        result = strategy.evaluate(ctx, regime, inputs)
        results.append(result)

    recommendations = _build_recommendations(inputs, results)

    return CompareResult(
        inputs_echo=inputs.model_dump(mode="json"),
        rules_version={
            "tax_year": rules["tax_year"],
            "last_updated": rules["last_updated"],
            "source": rules["source"],
        },
        results=results,
        recommendations=recommendations,
    )
