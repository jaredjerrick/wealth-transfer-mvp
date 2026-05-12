"""§529 Qualified Tuition Program.

Lifecycle:
  1. Contribution treated as a completed gift to beneficiary (§2511) eligible
     for §2503(b) annual exclusion. Optional §529(c)(2)(B) five-year forward
     election lets donor frontload up to 5× the annual exclusion in year one
     without using lifetime exemption.
  2. State income tax deduction at the contribution year (NY $5K/$10K;
     IL $10K/$20K; TX none).
  3. Tax-free growth under §529(c)(1).
  4. Tax-free qualified higher-education / K-12 distributions under §529(c)(3).
  5. Assets excluded from donor's gross estate under §529(c)(4) (donor retains
     control without inclusion — the unicorn property of 529s).
  6. SECURE 2.0 §126 allows up to $35,000 lifetime to roll to a Roth IRA for
     the beneficiary (subject to 15-year account age and annual IRA limits) —
     surfaced as an assumption flag for the MVP.

For headline number purposes, MVP assumes the corpus is used for qualified
education expenses (tax-free out). Non-qualified withdrawals would face the
§529(c)(6) 10% penalty + ordinary income on earnings — surfaced as a warning
if user later supplies a non-qualified usage flag.
"""

from __future__ import annotations

from decimal import Decimal

from ..citations import CITATIONS
from ..inputs import DonorInputs
from ..regimes.base import StateRegime
from ..tax_context import D, ZERO, TaxContext, round_cents
from .base import Strategy, StrategyResult, YearlyRow


class Section529Strategy(Strategy):
    name = "529 Plan"

    def evaluate(
        self,
        ctx: TaxContext,
        regime: StateRegime,
        inputs: DonorInputs,
    ) -> StrategyResult:
        annual_contribution = D(inputs.annual_contribution)
        horizon = inputs.investment_horizon_years
        r = D(inputs.expected_pretax_return)

        # ----- Gift-tax handling -----
        # 5-year election lets donor frontload up to 5× the annual exclusion
        # in year one. Tracked separately to surface in citations and
        # assumptions; the MVP does not deplete lifetime exemption unless the
        # contribution is large.
        annual_exclusion = ctx.annual_exclusion_total(num_donees=1)
        cites_gift: list = [CITATIONS["annual_exclusion"], CITATIONS["completed_gift"]]
        if inputs.elect_529_five_year and annual_contribution > annual_exclusion:
            cites_gift.append(CITATIONS["five_year_election_529"])

        # ----- State income tax deduction (benefit calculated at donor's marginal) -----
        state_deductible, state_ded_cites = regime.section_529_deduction(annual_contribution, inputs)
        # Approximate state benefit = deductible × state marginal income rate.
        # For flat-rate states this is exact; for graduated, we use the donor's
        # average state rate from total AGI as a reasonable proxy.
        if regime.code == "IL":
            state_marginal = D(regime.state_data["income_tax"]["flat_rate"])
        elif regime.code == "TX":
            state_marginal = ZERO
        else:  # NY
            agi_state_tax = regime.state_income_tax(D(inputs.donor_gross_income_agi), inputs).state_income_tax
            state_marginal = (agi_state_tax / D(inputs.donor_gross_income_agi)) if D(inputs.donor_gross_income_agi) > ZERO else ZERO

        annual_state_benefit = state_deductible * state_marginal  # treated as a negative drag

        # ----- Accumulation (tax-free) -----
        balance = ZERO
        contributions_to_date = ZERO
        cumulative_state_benefit = ZERO
        yearly: list[YearlyRow] = []

        for year in range(horizon):
            balance += annual_contribution
            contributions_to_date += annual_contribution
            balance += balance * r  # tax-free growth
            cumulative_state_benefit += annual_state_benefit
            yearly.append(YearlyRow(
                year_index=year,
                child_age=inputs.child_age + year,
                contributions_to_date=round_cents(contributions_to_date),
                pretax_balance=round_cents(balance),
                annual_tax_drag=ZERO,
                cumulative_tax_drag=round_cents(-cumulative_state_benefit),  # negative = benefit
            ))

        pretax_terminal = balance
        # Qualified distributions = tax-free → after-tax to recipient = pretax_terminal.
        # State income deduction is a *donor-side* benefit that reduces the donor's
        # tax bill; it does not increase the corpus but it does increase the donor's
        # net wealth, which in turn increases what flows to the heir on death. We
        # represent this as a separate "negative tax" line in the breakdown.

        breakdown = self._empty_breakdown()
        breakdown["state_income"] = round_cents(-cumulative_state_benefit)  # negative = saved
        # No federal/state estate tax on 529 corpus (§529(c)(4)).
        # No gift tax in normal usage (annual exclusion).

        after_tax_to_recipient = pretax_terminal

        citations = [
            CITATIONS["529_growth"],
            CITATIONS["529_qualified_distribution"],
            CITATIONS["529_estate_exclusion"],
            CITATIONS["annual_exclusion"],
            *cites_gift,
            *state_ded_cites,
        ]

        assumptions = [
            "Beneficiary uses corpus for qualified education expenses — distributions are federal-tax-free under §529(c)(3).",
            f"State income-tax deduction: ${round_cents(state_deductible)}/yr × state marginal rate ≈ ${round_cents(annual_state_benefit)} benefit/yr.",
            "Corpus excluded from donor's gross estate under §529(c)(4).",
            "SECURE 2.0 §126: up to $35,000 lifetime may be rolled to a Roth IRA for the beneficiary (subject to 15-year account age and annual IRA limits).",
        ]
        warnings = []
        if inputs.elect_529_five_year:
            assumptions.append(
                f"5-year forward election (§529(c)(2)(B)) elected — year 1 gift treated "
                f"as made ratably over 5 years for annual exclusion purposes."
            )

        if annual_contribution > annual_exclusion and not inputs.elect_529_five_year:
            warnings.append(
                f"Annual contribution ${annual_contribution:,.0f} exceeds annual exclusion "
                f"${annual_exclusion:,.0f}. Consider electing the §529(c)(2)(B) five-year "
                f"forward election to avoid using lifetime exemption."
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
