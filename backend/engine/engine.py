"""Top-level orchestrator. Runs all six strategies for the requested state."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from .inputs import DonorInputs
from .regimes import regime_for
from .strategies import ALL_STRATEGIES, StrategyResult
from .tax_context import TaxContext, load_rules


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------
# Structured representation of a planning recommendation. The category is the
# topical bucket (UI uses it for the card chip label and color). Priority lets
# the UI sort or visually weight items — "high" recs are estate-tax exposure
# issues with real dollar impact; "normal" are planning prompts; "low" are
# informational (e.g., "Roth path blocked because no earned income").
#
# Categories are a closed set — listed in CATEGORIES below. Add a new entry
# there before referencing it in a recommendation constructor, otherwise the
# frontend chip styling will fall through to the generic "Planning" treatment.

CATEGORY_ESTATE = "Estate"
CATEGORY_EDUCATION = "Education"
CATEGORY_FAMILY_EVENT = "Family event"
CATEGORY_CUSTODIAL = "Custodial"
CATEGORY_RETIREMENT = "Retirement"
CATEGORY_STEP_UP = "Step-up"
CATEGORY_GST = "GST"
CATEGORY_GIFTING = "Gifting"
CATEGORY_PLANNING = "Planning"

CATEGORIES = (
    CATEGORY_ESTATE,
    CATEGORY_EDUCATION,
    CATEGORY_FAMILY_EVENT,
    CATEGORY_CUSTODIAL,
    CATEGORY_RETIREMENT,
    CATEGORY_STEP_UP,
    CATEGORY_GST,
    CATEGORY_GIFTING,
    CATEGORY_PLANNING,
)

PRIORITY_HIGH = "high"
PRIORITY_NORMAL = "normal"
PRIORITY_LOW = "low"

# Sort order for output: highs before normals before lows. Within a priority
# bracket we preserve insertion order, so the engine code reads top-to-bottom.
_PRIORITY_RANK = {PRIORITY_HIGH: 0, PRIORITY_NORMAL: 1, PRIORITY_LOW: 2}


@dataclass(frozen=True)
class Recommendation:
    """A single rules-based planning recommendation surfaced on the dashboard.

    `category` and `priority` are produced server-side so the UI does not have
    to pattern-match the message text — that was previously a regex-based
    heuristic on the frontend, which would silently miscategorize any rewording.
    """

    message: str
    category: str = CATEGORY_PLANNING
    priority: str = PRIORITY_NORMAL

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "category": self.category,
            "priority": self.priority,
        }


@dataclass
class CompareResult:
    inputs_echo: dict
    rules_version: dict
    results: list[StrategyResult]
    recommendations: list[Recommendation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "inputs": self.inputs_echo,
            "rules_version": self.rules_version,
            "results": [r.to_dict() for r in self.results],
            "recommendations": [r.to_dict() for r in self.recommendations],
        }


def _build_recommendations(
    inputs: DonorInputs, results: list[StrategyResult]
) -> list[Recommendation]:
    """Rules-based suggestions surfaced on the dashboard. Not LLM-generated.

    Order of construction below is the order recs would appear if all were
    same-priority. The final list is stable-sorted by priority so high-impact
    estate items rise to the top regardless of where they appear in the code.
    """
    recs: list[Recommendation] = []

    # ---- Estate-tax exposure (HIGH priority — these are real dollars) ----
    if inputs.donor_net_worth > Decimal("7350000") and inputs.state.value == "NY":
        recs.append(
            Recommendation(
                message=(
                    "Donor's net worth is near or above the NY $7.35M estate exemption (2026) — "
                    "lifetime gifting strategies (annual exclusion + 5-year 529 election) "
                    "may reduce or eliminate the NY estate cliff exposure."
                ),
                category=CATEGORY_ESTATE,
                priority=PRIORITY_HIGH,
            )
        )
    if inputs.donor_net_worth > Decimal("4000000") and inputs.state.value == "IL":
        recs.append(
            Recommendation(
                message=(
                    "Donor exceeds the IL $4M estate exemption (not portable, not indexed). "
                    "Lifetime gifting and federal-state exemption mismatch warrant attention."
                ),
                category=CATEGORY_ESTATE,
                priority=PRIORITY_HIGH,
            )
        )
    if inputs.donor_net_worth > Decimal("15000000"):
        recs.append(
            Recommendation(
                message=(
                    "Donor's net worth exceeds the federal §2010 basic exclusion ($15.0M, 2026). "
                    "Federal estate tax exposure is material; consider lifetime gifting and §2031 "
                    "valuation planning. With a surviving spouse and a timely §2010(c)(2)(B) "
                    "portability election, the combined household exclusion is $30.0M."
                ),
                category=CATEGORY_ESTATE,
                priority=PRIORITY_HIGH,
            )
        )

    # ---- Custodial: UTMA control transfer ----
    age_of_majority = 21
    if inputs.child_age + inputs.investment_horizon_years > age_of_majority:
        years_to_majority = max(0, age_of_majority - inputs.child_age)
        recs.append(
            Recommendation(
                message=(
                    f"Child reaches state UTMA age of majority (21) at year {years_to_majority}. "
                    f"UTMA control transfers to the beneficiary at that point — model this in "
                    f"the UGMA/UTMA strategy and consider trust alternatives for longer-horizon control."
                ),
                category=CATEGORY_CUSTODIAL,
                priority=PRIORITY_NORMAL,
            )
        )

    # ---- Retirement: Roth blocking ----
    if inputs.child_earned_income <= Decimal("0"):
        recs.append(
            Recommendation(
                message=(
                    "Roth IRA path is blocked: child has no earned income (IRC §219(b), §408A(c)(2)). "
                    "If the child works (W-2 or self-employment), the Roth path becomes the most "
                    "tax-efficient long-horizon vehicle on a per-dollar basis."
                ),
                category=CATEGORY_RETIREMENT,
                priority=PRIORITY_LOW,
            )
        )

    # ---- Step-up: Community-property edge ----
    if inputs.state.value == "TX" and inputs.spouse_present:
        recs.append(
            Recommendation(
                message=(
                    "Married Texas donors receive a §1014(b)(6) double step-up on community "
                    "property at the first spouse's death — a meaningful capital-gains-tax saving "
                    "vs. equivalent New York or Illinois married donors."
                ),
                category=CATEGORY_STEP_UP,
                priority=PRIORITY_LOW,
            )
        )

    # ---- Life-event prompts ----
    # Inflate today's-dollar estimates to the year the event is expected to
    # happen, using the donor's inflation rate, so the planning headline shows
    # the dollar figure parents will actually face.
    infl = Decimal("1") + Decimal(str(inputs.inflation_rate))
    if inputs.plan_pay_college and inputs.child_expects_college:
        years_to_college = max(0, 18 - inputs.child_age)
        future_college = Decimal(str(inputs.est_college_cost_today)) * (
            infl ** years_to_college
        )
        recs.append(
            Recommendation(
                message=(
                    f"College: at the child's age 18 (in {years_to_college} years), today's "
                    f"${inputs.est_college_cost_today:,.0f} estimate inflates to ~${future_college:,.0f}. "
                    f"529 distributions for qualified higher-education expenses are federal-tax-free "
                    f"under §529(c)(3); pair with annual exclusion gifting or the 5-year forward election."
                ),
                category=CATEGORY_EDUCATION,
                priority=PRIORITY_NORMAL,
            )
        )
    if inputs.plan_pay_wedding:
        years_to_wedding = max(0, 28 - inputs.child_age)
        future_wedding = Decimal(str(inputs.est_wedding_cost_today)) * (
            infl ** years_to_wedding
        )
        recs.append(
            Recommendation(
                message=(
                    f"Wedding: a typical age-28 wedding (in {years_to_wedding} years) costing "
                    f"${inputs.est_wedding_cost_today:,.0f} today would be ~${future_wedding:,.0f} at the time. "
                    f"Direct vendor payments under §2503(e) (tuition/medical) do NOT cover weddings; "
                    f"plan to use the annual exclusion (§2503(b)) and/or lifetime exemption (§2010(c))."
                ),
                category=CATEGORY_FAMILY_EVENT,
                priority=PRIORITY_NORMAL,
            )
        )
    if inputs.plan_pay_first_home:
        years_to_home = max(0, 30 - inputs.child_age)
        future_home = Decimal(str(inputs.est_first_home_help_today)) * (
            infl ** years_to_home
        )
        recs.append(
            Recommendation(
                message=(
                    f"First home: ~${inputs.est_first_home_help_today:,.0f} of help today inflates to "
                    f"~${future_home:,.0f} in {years_to_home} years. A Roth IRA allows a $10,000 lifetime "
                    f"first-home distribution (§72(t)(2)(F)) without penalty; UTMA assets can also be used "
                    f"once the child reaches the age of majority."
                ),
                category=CATEGORY_FAMILY_EVENT,
                priority=PRIORITY_NORMAL,
            )
        )

    # ---- Gifting: annual-exclusion headroom across multiple donees ----
    if inputs.num_children > 1:
        per = Decimal("19000")  # §2503(b) annual exclusion — matches the value carried in the rules file.
        with_split = (
            (per * 2) if inputs.elect_gift_splitting and inputs.spouse_present else per
        )
        total = with_split * Decimal(str(inputs.num_children))
        recs.append(
            Recommendation(
                message=(
                    f"With {inputs.num_children} children, the household's annual exclusion headroom is "
                    f"approximately ${total:,.0f}/yr "
                    f"({'with' if (inputs.elect_gift_splitting and inputs.spouse_present) else 'without'} "
                    f"spousal gift-splitting). Spreading gifts across donees materially expands lifetime "
                    f"transfer capacity without touching §2010 exemption."
                ),
                category=CATEGORY_GIFTING,
                priority=PRIORITY_NORMAL,
            )
        )

    # ---- GST: Generation-skipping election ----
    if inputs.elect_skip_generation:
        recs.append(
            Recommendation(
                message=(
                    "Skip-generation election (recipient is a grandchild or later): GST tax (§§2611, "
                    "2631, 2641) is applied on top of estate tax on non-exempt strategies. Direct-skip "
                    "gifts via §2503(b) annual exclusion qualify for the §2642(c) GST annual exclusion "
                    "in most cases — see the GRAT / dynasty-trust explainer for the more powerful "
                    "leveraged options."
                ),
                category=CATEGORY_GST,
                priority=PRIORITY_NORMAL,
            )
        )

    # ---- Retirement-age check (interaction with traditional accounts). ----
    if inputs.planned_retirement_age is not None:
        years_to_retirement = inputs.planned_retirement_age - inputs.donor_age
        if years_to_retirement < inputs.investment_horizon_years:
            recs.append(
                Recommendation(
                    message=(
                        f"Planned retirement in {years_to_retirement} years is sooner than the "
                        f"{inputs.investment_horizon_years}-year planning horizon — model whether you'll be "
                        f"taking IRA distributions during the accumulation window, which would compress "
                        f"Traditional-IRA vehicle returns."
                    ),
                    category=CATEGORY_RETIREMENT,
                    priority=PRIORITY_NORMAL,
                )
            )

    # Stable sort by priority so high-impact items surface first regardless of
    # the order they were appended above.
    recs.sort(key=lambda r: _PRIORITY_RANK.get(r.priority, 99))
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
