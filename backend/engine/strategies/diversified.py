"""Diversified Portfolio — composite strategy that splits the annual contribution
across multiple vehicles per the user's allocation.

This is not a new tax regime — it's a weighted combination of the existing
strategies. The composite re-uses the individual strategy modules: for each
allocated vehicle, we run that strategy with a modified inputs where
`annual_contribution` is the allocated share (and `existing_balances` is the
vehicle's existing balance only). We then sum the after-tax-to-recipient
values and the tax breakdowns.

This means the diversified result inherits every rule each underlying
strategy enforces (Roth earned-income block, 529 aggregate cap, Trump
parent cap, kiddie tax, GST, estate-tax slice) without any duplication of
math. The cost: cap interactions across vehicles (e.g., the user-perceived
"Roth" allocation in excess of the IRA limit is silently dropped by the
Roth strategy) are surfaced as the same warnings the user would see in the
standalone Roth row.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List

from ..citations import Citation, CITATIONS
from ..inputs import AllocationItem, DonorInputs, VehicleKey
from ..regimes.base import StateRegime
from ..tax_context import D, ZERO, TaxContext, round_cents
from .base import Strategy, StrategyResult, YearlyRow, TaxExplanation
from .explain import build_tax_explanations


# Vehicle key → Strategy class. Built lazily inside `evaluate` to avoid the
# circular-import edge that would arise from importing the strategies at
# module-load time (the `__init__` exports happen *after* this file is loaded
# if we import there).
def _vehicle_to_strategy_cls():
    from .taxable_brokerage import TaxableBrokerageStrategy
    from .hold_until_death import HoldUntilDeathStrategy
    from .section_529 import Section529Strategy
    from .ugma_utma import UGMAUTMAStrategy
    from .traditional_ira import TraditionalIRAStrategy
    from .roth_ira import RothIRAStrategy
    from .trump_account import TrumpAccountStrategy
    return {
        VehicleKey.TAXABLE: TaxableBrokerageStrategy,
        VehicleKey.HOLD: HoldUntilDeathStrategy,
        VehicleKey.SEC_529: Section529Strategy,
        VehicleKey.UGMA: UGMAUTMAStrategy,
        VehicleKey.TRAD_IRA: TraditionalIRAStrategy,
        VehicleKey.ROTH_IRA: RothIRAStrategy,
        VehicleKey.TRUMP: TrumpAccountStrategy,
    }


class DiversifiedPortfolioStrategy(Strategy):
    name = "Diversified Portfolio"

    def evaluate(
        self,
        ctx: TaxContext,
        regime: StateRegime,
        inputs: DonorInputs,
    ) -> StrategyResult:
        # No allocation supplied → strategy not available.
        if not inputs.allocation:
            return StrategyResult(
                strategy_name=self.name,
                contribution_total=ZERO,
                pretax_terminal_value=ZERO,
                taxes_paid_breakdown=self._empty_breakdown(),
                after_tax_wealth_to_recipient=ZERO,
                effective_tax_rate=ZERO,
                year_by_year_projection=[],
                citations=[],
                assumptions=[],
                is_available=False,
                unavailable_reason=(
                    "No diversified allocation supplied. Pick a preset portfolio "
                    "or enter a custom split across vehicles."
                ),
            )

        vehicle_to_cls = _vehicle_to_strategy_cls()
        per_vehicle_results: list[tuple[AllocationItem, StrategyResult]] = []

        horizon = inputs.investment_horizon_years

        for item in inputs.allocation:
            if item.annual_amount <= ZERO:
                continue
            cls = vehicle_to_cls[item.vehicle]

            # Synthesize a per-vehicle inputs object: same as the donor's
            # inputs, but with annual_contribution set to the allocated amount
            # AND existing_balances filtered to this vehicle only (so we don't
            # double-count seed balances across rows).
            existing_for_vehicle = inputs.existing_balances.get(item.vehicle, Decimal("0"))
            per_vehicle_inputs = inputs.model_copy(
                update={
                    "annual_contribution": item.annual_amount,
                    "existing_balances": {item.vehicle: D(existing_for_vehicle)} if existing_for_vehicle else {},
                    # Diversified rows shouldn't recurse into another diversified.
                    "allocation": None,
                }
            )
            res = cls().evaluate(ctx, regime, per_vehicle_inputs)
            per_vehicle_results.append((item, res))

        if not per_vehicle_results:
            return StrategyResult(
                strategy_name=self.name,
                contribution_total=ZERO,
                pretax_terminal_value=ZERO,
                taxes_paid_breakdown=self._empty_breakdown(),
                after_tax_wealth_to_recipient=ZERO,
                effective_tax_rate=ZERO,
                year_by_year_projection=[],
                citations=[],
                assumptions=[],
                is_available=False,
                unavailable_reason="All allocation amounts are zero — nothing to model.",
            )

        # ----- aggregate -----
        breakdown = self._empty_breakdown()
        contribution_total = ZERO
        pretax_terminal = ZERO
        after_tax = ZERO
        citations: list[Citation] = []
        assumptions: list[str] = ["Composite of the individual-vehicle strategies, summed."]
        warnings: list[str] = []
        explanations: list[TaxExplanation] = []
        for item, res in per_vehicle_results:
            if not res.is_available:
                warnings.append(
                    f"{item.vehicle.value}: ${D(item.annual_amount):,.0f}/yr ignored — "
                    f"{res.unavailable_reason}"
                )
                continue
            contribution_total += D(res.contribution_total)
            pretax_terminal += D(res.pretax_terminal_value)
            after_tax += D(res.after_tax_wealth_to_recipient)
            for k, v in res.taxes_paid_breakdown.items():
                breakdown[k] = D(breakdown[k]) + D(v)
            citations.extend(res.citations)
            assumptions.extend(
                f"[{item.vehicle.value}] {a}" for a in res.assumptions
            )
            warnings.extend(
                f"[{item.vehicle.value}] {w}" for w in res.warnings
            )
            for ex in res.tax_explanations:
                explanations.append(
                    TaxExplanation(
                        line=ex.line,
                        label=f"{ex.label} (from {item.vehicle.value})",
                        amount=ex.amount,
                        rationale=ex.rationale,
                    )
                )

        # Build a synthetic year-by-year projection by summing the per-vehicle
        # pretax_balance per year. This gives the user a single accumulation
        # line for the diversified composite.
        yearly: list[YearlyRow] = []
        for y in range(horizon):
            total_contrib = ZERO
            total_balance = ZERO
            total_drag = ZERO
            cumulative_drag = ZERO
            child_age_this_year = inputs.child_age + y
            for _item, res in per_vehicle_results:
                if not res.is_available:
                    continue
                if y < len(res.year_by_year_projection):
                    row = res.year_by_year_projection[y]
                    total_contrib += D(row.contributions_to_date)
                    total_balance += D(row.pretax_balance)
                    total_drag += D(row.annual_tax_drag)
                    cumulative_drag += D(row.cumulative_tax_drag)
            yearly.append(YearlyRow(
                year_index=y,
                child_age=child_age_this_year,
                contributions_to_date=round_cents(total_contrib),
                pretax_balance=round_cents(total_balance),
                annual_tax_drag=round_cents(total_drag),
                cumulative_tax_drag=round_cents(cumulative_drag),
            ))

        # Round breakdown for cleanliness.
        breakdown = {k: round_cents(D(v)) for k, v in breakdown.items()}

        # If we have a composite rationale we want shown at the top of the
        # explainer list, prepend it.
        composite_rationale = (
            f"Composite of {len(per_vehicle_results)} vehicles. Each line below "
            f"shows the tax paid by a specific vehicle in the mix; the rationale "
            f"is the same as it would be if you'd picked that vehicle on its own."
        )
        explanations = [TaxExplanation(
            line="__composite__",
            label="How this composite was built",
            amount=ZERO,
            rationale=composite_rationale,
        )] + explanations

        return StrategyResult(
            strategy_name=self.name,
            contribution_total=round_cents(contribution_total),
            pretax_terminal_value=round_cents(pretax_terminal),
            taxes_paid_breakdown=breakdown,
            after_tax_wealth_to_recipient=round_cents(after_tax),
            effective_tax_rate=self._effective_tax_rate(breakdown, contribution_total, pretax_terminal),
            year_by_year_projection=yearly,
            citations=citations,
            assumptions=assumptions,
            warnings=warnings,
            tax_explanations=explanations,
        )
