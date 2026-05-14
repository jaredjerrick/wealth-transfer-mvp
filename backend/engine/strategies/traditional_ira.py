"""Traditional IRA funded for the child by donor as gift.

Lifecycle:
  1. Child must have earned income (§219(b)). Contribution limited to lesser of
     IRA limit ($7,000 for 2025) or earned income.
  2. Contribution is a gift to the child (§2511); §2503(b) annual exclusion
     applies. Child gets the §219 deduction on their own return (small benefit
     given typical young-adult AGI).
  3. Tax-deferred growth. Ordinary income tax on withdrawal (§408(d)).
  4. **No §1014 step-up at donor's death** — Income in Respect of a Decedent
     under §691 means the embedded ordinary income passes through to the heir.
  5. SECURE Act 10-year rule (§401(a)(9)(H)): non-spouse beneficiaries must
     distribute within 10 years.
  6. Terminal value to recipient is reduced by ordinary income tax at the
     recipient's marginal rate. MVP uses the donor's marginal rate as a proxy
     (treating the recipient as inheriting in their adult earning years).
"""

from __future__ import annotations

from decimal import Decimal

from ..citations import CITATIONS
from ..inputs import DonorInputs
from ..regimes.base import StateRegime
from ..tax_context import D, ZERO, TaxContext, round_cents
from .base import Strategy, StrategyResult, YearlyRow
from .explain import build_tax_explanations
from ..inputs import VehicleKey


class TraditionalIRAStrategy(Strategy):
    name = "Traditional IRA"

    def evaluate(
        self,
        ctx: TaxContext,
        regime: StateRegime,
        inputs: DonorInputs,
    ) -> StrategyResult:
        # ----- Earned-income hard block (§219(b)) -----
        if inputs.child_earned_income <= ZERO:
            return StrategyResult(
                strategy_name=self.name,
                contribution_total=ZERO,
                pretax_terminal_value=ZERO,
                taxes_paid_breakdown=self._empty_breakdown(),
                after_tax_wealth_to_recipient=ZERO,
                effective_tax_rate=ZERO,
                year_by_year_projection=[],
                citations=[CITATIONS["ira_earned_income"]],
                assumptions=[],
                is_available=False,
                unavailable_reason=(
                    "Traditional IRA requires the child to have earned income "
                    "(IRC §219(b)). Set child_earned_income > 0 to enable."
                ),
            )

        annual_contribution_cap = min(
            D(inputs.annual_contribution),
            ctx.ira_limit,
            D(inputs.child_earned_income),
        )

        horizon = inputs.investment_horizon_years
        r = D(inputs.expected_pretax_return)

        existing = D(inputs.existing_balances.get(VehicleKey.TRAD_IRA, 0))
        balance = existing
        contributions_to_date = ZERO
        yearly: list[YearlyRow] = []

        for year in range(horizon):
            balance += annual_contribution_cap
            contributions_to_date += annual_contribution_cap
            balance += balance * r  # tax-deferred
            yearly.append(YearlyRow(
                year_index=year,
                child_age=inputs.child_age + year,
                contributions_to_date=round_cents(contributions_to_date),
                pretax_balance=round_cents(balance),
                annual_tax_drag=ZERO,
                cumulative_tax_drag=ZERO,
            ))

        pretax_terminal = balance

        # No §1014 step-up — full embedded gain taxed as ordinary income (IRD).
        # Use donor's marginal as proxy for recipient's eventual rate.
        donor_marginal = ctx.federal_ordinary_marginal_rate(D(inputs.donor_gross_income_agi))
        federal_income_tax_on_distribution = pretax_terminal * donor_marginal

        # State income tax on distribution (recipient's state — MVP uses donor's state).
        state_tax_on_distribution = regime.state_income_tax(pretax_terminal, inputs).state_income_tax

        after_tax_to_recipient = pretax_terminal - federal_income_tax_on_distribution - state_tax_on_distribution

        breakdown = self._empty_breakdown()
        breakdown["income"] = round_cents(federal_income_tax_on_distribution)
        breakdown["state_income"] = round_cents(state_tax_on_distribution)

        citations = [
            CITATIONS["ira_earned_income"],
            CITATIONS["traditional_ira_distribution"],
            CITATIONS["ird_no_step_up"],
            CITATIONS["secure_10_year"],
            CITATIONS["completed_gift"],
            CITATIONS["annual_exclusion"],
        ]

        assumptions = [
            f"Annual contribution capped at min(${inputs.annual_contribution:,.0f}, "
            f"${ctx.ira_limit}, child earned income ${inputs.child_earned_income:,.0f}) = "
            f"${annual_contribution_cap:,.0f}.",
            "Tax-deferred growth; ordinary income on distribution (§408(d)).",
            "No §1014 step-up — IRD treatment under §691 means embedded gain remains ordinary income.",
            "Non-spouse beneficiary must withdraw fully within 10 years of donor's death (SECURE Act §401(a)(9)(H)).",
            f"Distribution taxed at donor's marginal rate as proxy for recipient ({donor_marginal * 100:.1f}% federal).",
        ]

        warnings: list[str] = []
        if D(inputs.annual_contribution) > ctx.ira_limit:
            warnings.append(
                f"Annual contribution input (${inputs.annual_contribution:,.0f}) exceeds "
                f"the IRA limit ($7,000 for 2025). Excess assumed redirected elsewhere — "
                f"not modeled in this strategy's corpus."
            )

        if existing > ZERO:
            assumptions.append(
                f"Starting corpus: ${existing:,.0f} of existing Traditional IRA balance seeded at year 0."
            )

        rationales = {
            "income": (
                f"Embedded ordinary-income tax (IRD, §691) — there is no §1014 step-up on a Traditional IRA. "
                f"Recipient's ordinary federal rate is proxied at the donor's marginal "
                f"({donor_marginal * 100:.1f}%)."
            ),
            "state_income": f"{regime.name} state income tax on the distribution.",
        }

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
            tax_explanations=build_tax_explanations(breakdown, rationales),
        )
