"""UGMA / UTMA custodial account.

Lifecycle:
  1. Contribution is a completed gift to the minor (§2511); §2503(b) annual
     exclusion applies.
  2. Account is in the child's name with a custodian. Income on account is
     taxable to the child.
  3. Kiddie tax (§1(g)): unearned income > $2,700 (sourced from the loaded rules
     file) is taxed at the parent's marginal rate until the child turns 19
     (24 if full-time student).
  4. If the donor serves as custodian and dies before age of majority, §2038
     pulls the account back into the donor's estate.
  5. At the state UTMA age of majority (NY 21, IL 21, TX 21), control transfers
     to the beneficiary irrevocably.
  6. Carryover basis (§1015) — recipient inherits donor's basis. §1014 step-up
     applies only at recipient's death (not relevant for the MVP terminal value).
"""

from __future__ import annotations

from decimal import Decimal

from ..citations import CITATIONS, Citation
from ..inputs import DonorInputs
from ..regimes.base import StateRegime
from ..tax_context import D, ZERO, TaxContext, round_cents
from .base import Strategy, StrategyResult, YearlyRow
from .explain import build_tax_explanations
from ..inputs import VehicleKey


class UGMAUTMAStrategy(Strategy):
    name = "UGMA/UTMA"

    def evaluate(
        self,
        ctx: TaxContext,
        regime: StateRegime,
        inputs: DonorInputs,
    ) -> StrategyResult:
        annual_contribution = D(inputs.annual_contribution)
        horizon = inputs.investment_horizon_years
        r = D(inputs.expected_pretax_return)
        dividend_yield = D(ctx.defaults["dividend_yield"])
        qualified_fraction = D(ctx.defaults["qualified_dividend_fraction"])
        turnover = D(ctx.defaults["annual_portfolio_turnover"])
        lt_fraction = D(ctx.defaults["long_term_gain_fraction_of_realized"])

        age_of_majority = regime.utma_age_of_majority

        existing = D(inputs.existing_balances.get(VehicleKey.UGMA, 0))
        balance = existing
        cost_basis = existing
        contributions_to_date = ZERO
        cumulative_drag = ZERO
        cumulative_income_tax = ZERO
        cumulative_cap_gains_tax = ZERO
        cumulative_state_income_tax = ZERO

        yearly: list[YearlyRow] = []

        donor_agi = D(inputs.donor_gross_income_agi)
        parent_marginal = ctx.federal_ordinary_marginal_rate(donor_agi)
        ltcg_rate_parent = ctx.federal_ltcg_rate(donor_agi)

        warnings: list[str] = []
        kiddie_warning_emitted = False
        majority_warning_emitted = False

        for year in range(horizon):
            balance += annual_contribution
            cost_basis += annual_contribution
            contributions_to_date += annual_contribution
            gross_growth = balance * r
            balance += gross_growth

            div_income = balance * dividend_yield / (D("1") + r)
            qualified_div = div_income * qualified_fraction
            ordinary_div = div_income * (D("1") - qualified_fraction)

            unrealized = balance - cost_basis
            realized_gains = unrealized * turnover if unrealized > ZERO else ZERO
            lt_gains = realized_gains * lt_fraction
            st_gains = realized_gains * (D("1") - lt_fraction)
            cost_basis += realized_gains

            child_age_this_year = inputs.child_age + year
            kiddie_applies = child_age_this_year < 19

            # Federal: apply kiddie tax to total unearned income above the floor.
            unearned_income_total = ordinary_div + st_gains + qualified_div + lt_gains
            if kiddie_applies:
                kiddie_tax_year, _ = ctx.apply_kiddie_tax(
                    unearned_income_total,
                    child_age=child_age_this_year,
                )
                federal_drag = kiddie_tax_year
                if unearned_income_total > ctx.kiddie_tax_floor and not kiddie_warning_emitted:
                    warnings.append(
                        f"Kiddie tax (§1(g)) triggered starting year {year}: unearned income "
                        f"of ${unearned_income_total:,.0f} exceeds the $2,700 floor; excess taxed at parent's marginal rate."
                    )
                    kiddie_warning_emitted = True
            else:
                # Child is taxed as adult — for MVP, approximate at child's lowest brackets.
                # The child filing single has its own standard deduction. We use 12% ordinary
                # / 0% LTCG as a reasonable estimate for a young adult with no other income.
                federal_drag = (ordinary_div + st_gains) * D("0.12") + (qualified_div + lt_gains) * D("0.00")
                if not majority_warning_emitted and child_age_this_year >= age_of_majority:
                    warnings.append(
                        f"Child reaches age of majority (year {year}) — UTMA custodial control "
                        f"transfers to the beneficiary irrevocably under state law."
                    )
                    majority_warning_emitted = True

            # State income tax on unearned income — taxed to the child but in
            # most graduated states this is small in absolute terms. MVP applies
            # the donor's state rate as a conservative upper bound.
            state_drag = regime.state_capital_gains_tax(unearned_income_total, inputs).state_income_tax

            year_drag = federal_drag + state_drag
            balance -= year_drag
            cumulative_drag += year_drag
            cumulative_income_tax += federal_drag * (ordinary_div + st_gains) / unearned_income_total if unearned_income_total > ZERO else ZERO
            cumulative_cap_gains_tax += federal_drag - (federal_drag * (ordinary_div + st_gains) / unearned_income_total if unearned_income_total > ZERO else ZERO)
            cumulative_state_income_tax += state_drag

            yearly.append(YearlyRow(
                year_index=year,
                child_age=child_age_this_year,
                contributions_to_date=round_cents(contributions_to_date),
                pretax_balance=round_cents(balance),
                annual_tax_drag=round_cents(year_drag),
                cumulative_tax_drag=round_cents(cumulative_drag),
            ))

        pretax_terminal = balance

        # Carryover basis → recipient sells with embedded gain at child's LTCG rate.
        # MVP assumption: child sells immediately at majority. Embedded gain =
        # pretax_terminal − cost_basis. Tax at 0% LTCG (assuming child has low income).
        embedded_gain = pretax_terminal - cost_basis
        recipient_capgains_tax = embedded_gain * D("0") if embedded_gain > ZERO else ZERO  # 0% bracket
        # (User can revisit; we surface as an assumption.)

        after_tax_to_recipient = pretax_terminal - recipient_capgains_tax

        # No estate inclusion (gift was completed) — unless donor=custodian and
        # dies before majority. MVP flags this as an assumption rather than
        # implementing the §2038 mechanic.

        breakdown = self._empty_breakdown()
        breakdown["income"] = round_cents(cumulative_income_tax)
        breakdown["capital_gains"] = round_cents(cumulative_cap_gains_tax + recipient_capgains_tax)
        breakdown["state_income"] = round_cents(cumulative_state_income_tax)

        citations = [
            CITATIONS["completed_gift"],
            CITATIONS["annual_exclusion"],
            CITATIONS["kiddie_tax"],
            CITATIONS["gift_basis"],
            CITATIONS["custodian_estate_inclusion"],
            CITATIONS["ordinary_rates"],
            CITATIONS["capital_gains_rates"],
        ]

        assumptions = [
            f"UTMA age of majority in {regime.name}: {age_of_majority}.",
            "Kiddie tax (§1(g)) applied while child is under 19.",
            "Donor is not also the custodian, avoiding §2038 estate inclusion. If donor=custodian and dies before majority, custodial property is pulled back into donor's estate.",
            "Carryover basis (§1015) — recipient inherits donor's basis. MVP assumes immediate sale at majority with embedded gain taxed at 0% LTCG bracket (child has low income).",
        ]

        if existing > ZERO:
            assumptions.append(
                f"Starting corpus: ${existing:,.0f} of existing UGMA/UTMA balance seeded at year 0 with full basis."
            )
        if inputs.elect_skip_generation:
            assumptions.append(
                "Direct-skip UGMA gifts to a grandchild typically qualify for the §2503(b) annual "
                "exclusion and GST exemption allocation under §2632 — MVP assumes the gift is fully "
                "GST-sheltered, so no incremental GST tax is shown."
            )

        rationales = {
            "income": "Kiddie tax (§1(g)) on unearned income above the $2,700 floor — taxed at parent's marginal rate while child is under 19.",
            "capital_gains": "Embedded gain on the carryover-basis corpus; recipient sells at the 0% LTCG bracket (assumed low income in MVP).",
            "state_income": f"{regime.name} tax on the child's unearned income.",
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
