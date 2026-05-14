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

    # ---- Life-event prompts ----
    # Inflate today's-dollar estimates to the year the event is expected to
    # happen, using the donor's inflation rate, so the planning headline shows
    # the dollar figure parents will actually face.
    infl = Decimal("1") + Decimal(str(inputs.inflation_rate))
    if inputs.plan_pay_college and inputs.child_expects_college:
        years_to_college = max(0, 18 - inputs.child_age)
        future_college = Decimal(str(inputs.est_college_cost_today)) * (infl ** years_to_college)
        recs.append(
            f"College: at the child's age 18 (in {years_to_college} years), today's "
            f"${inputs.est_college_cost_today:,.0f} estimate inflates to ~${future_college:,.0f}. "
            f"529 distributions for qualified higher-education expenses are federal-tax-free "
            f"under §529(c)(3); pair with annual exclusion gifting or the 5-year forward election."
        )
    if inputs.plan_pay_wedding:
        years_to_wedding = max(0, 28 - inputs.child_age)
        future_wedding = Decimal(str(inputs.est_wedding_cost_today)) * (infl ** years_to_wedding)
        recs.append(
            f"Wedding: a typical age-28 wedding (in {years_to_wedding} years) costing "
            f"${inputs.est_wedding_cost_today:,.0f} today would be ~${future_wedding:,.0f} at the time. "
            f"Direct vendor payments under §2503(e) (tuition/medical) do NOT cover weddings; "
            f"plan to use the annual exclusion (§2503(b)) and/or lifetime exemption (§2010(c))."
        )
    if inputs.plan_pay_first_home:
        years_to_home = max(0, 30 - inputs.child_age)
        future_home = Decimal(str(inputs.est_first_home_help_today)) * (infl ** years_to_home)
        recs.append(
            f"First home: ~${inputs.est_first_home_help_today:,.0f} of help today inflates to "
            f"~${future_home:,.0f} in {years_to_home} years. A Roth IRA allows a $10,000 lifetime "
            f"first-home distribution (§72(t)(2)(F)) without penalty; UTMA assets can also be used "
            f"once the child reaches the age of majority."
        )

    # Number of children — affects annual-exclusion headroom.
    if inputs.num_children > 1:
        per = Decimal("19000")  # 2025 annual exclusion per §2503(b); display-only
        with_split = (per * 2) if inputs.elect_gift_splitting and inputs.spouse_present else per
        total = with_split * Decimal(str(inputs.num_children))
        recs.append(
            f"With {inputs.num_children} children, the household's annual exclusion headroom is "
            f"approximately ${total:,.0f}/yr "
            f"({'with' if (inputs.elect_gift_splitting and inputs.spouse_present) else 'without'} "
            f"spousal gift-splitting). Spreading gifts across donees materially expands lifetime "
            f"transfer capacity without touching §2010 exemption."
        )

    # Generation-skipping
    if inputs.elect_skip_generation:
        recs.append(
            "Skip-generation election (recipient is a grandchild or later): GST tax (§§2611, "
            "2631, 2641) is applied on top of estate tax on non-exempt strategies. Direct-skip "
            "gifts via §2503(b) annual exclusion qualify for the §2642(c) GST annual exclusion "
            "in most cases — see the GRAT / dynasty-trust explainer for the more powerful "
            "leveraged options."
        )

    # Retirement-age check (interaction with traditional accounts).
    if inputs.planned_retirement_age is not None:
        years_to_retirement = inputs.planned_retirement_age - inputs.donor_age
        if years_to_retirement < inputs.investment_horizon_years:
            recs.append(
                f"Planned retirement in {years_to_retirement} years is sooner than the "
                f"{inputs.investment_horizon_years}-year planning horizon — model whether you'll be "
                f"taking IRA distributions during the accumulation window, which would compress "
                f"Traditional-IRA vehicle returns."
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
