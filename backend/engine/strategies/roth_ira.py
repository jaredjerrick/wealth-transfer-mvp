"""Roth IRA funded for the child by donor as gift.

Lifecycle:
  1. Child must have earned income (§408A(c)(2)). Contribution limited to lesser
     of IRA limit ($7,000 for 2025) or earned income.
  2. Contribution is a gift (§2511); §2503(b) annual exclusion applies.
  3. Tax-free growth.
  4. Qualified distributions tax-free under §408A(d) (5-year holding + age 59½
     or death/disability/first-home).
  5. Estate inclusion at donor's death: NONE (asset belongs to the child from
     the moment of gift).
  6. Recipient (the child) inherits the account directly (or it remains theirs)
     — terminal value is the full corpus.

This is the most tax-efficient long-horizon vehicle on a per-dollar basis when
the earned-income condition is satisfied, particularly for very young children
with decades of compounding ahead.
"""

from __future__ import annotations

from decimal import Decimal

from ..citations import CITATIONS
from ..inputs import DonorInputs
from ..regimes.base import StateRegime
from ..tax_context import D, ZERO, TaxContext, round_cents
from .base import Strategy, StrategyResult, YearlyRow


class RothIRAStrategy(Strategy):
    name = "Roth IRA (Custodial)"

    def evaluate(
        self,
        ctx: TaxContext,
        regime: StateRegime,
        inputs: DonorInputs,
    ) -> StrategyResult:
        # ----- Earned-income hard block (§219(b), §408A(c)(2)) -----
        if inputs.child_earned_income <= ZERO:
            return StrategyResult(
                strategy_name=self.name,
                contribution_total=ZERO,
                pretax_terminal_value=ZERO,
                taxes_paid_breakdown=self._empty_breakdown(),
                after_tax_wealth_to_recipient=ZERO,
                effective_tax_rate=ZERO,
                year_by_year_projection=[],
                citations=[CITATIONS["ira_earned_income"], CITATIONS["roth_earned_income"]],
                assumptions=[],
                is_available=False,
                unavailable_reason=(
                    "Roth IRA requires the child to have earned income "
                    "(IRC §219(b), §408A(c)(2)). Set child_earned_income > 0 to enable."
                ),
            )

        annual_contribution_cap = min(
            D(inputs.annual_contribution),
            ctx.ira_limit,
            D(inputs.child_earned_income),
        )

        horizon = inputs.investment_horizon_years
        r = D(inputs.expected_pretax_return)

        balance = ZERO
        contributions_to_date = ZERO
        yearly: list[YearlyRow] = []

        for year in range(horizon):
            balance += annual_contribution_cap
            contributions_to_date += annual_contribution_cap
            balance += balance * r  # tax-free growth
            yearly.append(YearlyRow(
                year_index=year,
                child_age=inputs.child_age + year,
                contributions_to_date=round_cents(contributions_to_date),
                pretax_balance=round_cents(balance),
                annual_tax_drag=ZERO,
                cumulative_tax_drag=ZERO,
            ))

        pretax_terminal = balance
        # Qualified distributions are tax-free. Asset never in donor's estate.
        after_tax_to_recipient = pretax_terminal

        breakdown = self._empty_breakdown()
        # No taxes paid in normal lifecycle.

        citations = [
            CITATIONS["roth_earned_income"],
            CITATIONS["roth_qualified_distribution"],
            CITATIONS["secure_10_year"],
            CITATIONS["completed_gift"],
            CITATIONS["annual_exclusion"],
        ]

        assumptions = [
            f"Annual contribution capped at min(${inputs.annual_contribution:,.0f}, "
            f"${ctx.ira_limit}, child earned income ${inputs.child_earned_income:,.0f}) = "
            f"${annual_contribution_cap:,.0f}.",
            "Tax-free growth and qualified distributions (§408A(d)).",
            "Account belongs to child from inception — not includible in donor's estate.",
            "Non-spouse beneficiary subject to SECURE 10-year rule, but distributions remain tax-free.",
        ]

        warnings: list[str] = []
        if D(inputs.annual_contribution) > ctx.ira_limit:
            warnings.append(
                f"Annual contribution input (${inputs.annual_contribution:,.0f}) exceeds "
                f"the IRA limit ($7,000 for 2025). Excess assumed redirected elsewhere — "
                f"not modeled in this strategy's corpus."
            )
        if D(inputs.annual_contribution) > D(inputs.child_earned_income):
            warnings.append(
                f"Annual contribution input (${inputs.annual_contribution:,.0f}) exceeds "
                f"child's earned income (${inputs.child_earned_income:,.0f}). Contribution "
                f"capped at earned income per §408A(c)(2)."
            )

        return StrategyResult(
            strategy_name=self.name,
            contribution_total=round_cents(contributions_to_date),
            pretax_terminal_value=round_cents(pretax_terminal),
            taxes_paid_breakdown=breakdown,
            after_tax_wealth_to_recipient=round_cents(after_tax_to_recipient),
            effective_tax_rate=self._effective_tax_rate(breakdown, contributions_to_date, pretax_terminal),
            year_by_year_projection=yearly,
            citations=citations,
            assumptions=assumptions,
            warnings=warnings,
        )
