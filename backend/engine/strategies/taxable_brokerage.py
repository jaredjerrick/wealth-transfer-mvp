"""Taxable brokerage account held by the donor until death.

Lifecycle:
  1. Donor contributes annually from after-tax income (no upfront tax benefit).
  2. Annual tax drag during accumulation:
        - Dividend yield × portfolio × qualified-dividend-rate (federal LTCG rate
          for qualified portion; ordinary rate for non-qualified portion).
        - Realized capital gains from portfolio turnover.
        - NIIT at 3.8% if donor's AGI > §1411 threshold.
        - State income tax on dividends and realized gains.
  3. At end of horizon, donor dies. Asset receives §1014 step-up to FMV
     (community-property states get the §1014(b)(6) double step-up if married).
  4. Asset is included in gross estate under §§2031–2033. Unified credit
     under §2010 applies, marital deduction under §2056 if spouse present
     (we model bequest to children for the planning question — no marital).
  5. State estate tax applies per regime (NY cliff, IL $4M, TX none).
  6. After-tax wealth to recipient is the post-estate-tax residual.
"""

from __future__ import annotations

from decimal import Decimal

from ..citations import Citation, CITATIONS
from ..inputs import DonorInputs
from ..regimes.base import StateRegime
from ..tax_context import D, ZERO, TaxContext, round_cents
from .base import Strategy, StrategyResult, YearlyRow


class TaxableBrokerageStrategy(Strategy):
    name = "Taxable Brokerage"

    def evaluate(
        self,
        ctx: TaxContext,
        regime: StateRegime,
        inputs: DonorInputs,
    ) -> StrategyResult:
        # ----- assumption resolution -----
        annual_contribution = D(inputs.annual_contribution)
        horizon = inputs.investment_horizon_years
        r = D(inputs.expected_pretax_return)
        dividend_yield = D(ctx.defaults["dividend_yield"])
        qualified_fraction = D(ctx.defaults["qualified_dividend_fraction"])
        turnover = D(ctx.defaults["annual_portfolio_turnover"])
        lt_fraction = D(ctx.defaults["long_term_gain_fraction_of_realized"])

        donor_agi = D(inputs.donor_gross_income_agi)
        ltcg_rate = ctx.federal_ltcg_rate(donor_agi)
        ordinary_marginal = ctx.federal_ordinary_marginal_rate(donor_agi)
        niit_rate = ctx.niit_rate_applies(donor_agi)

        # ----- accumulation loop -----
        balance = ZERO
        cost_basis = ZERO
        contributions_to_date = ZERO
        cumulative_income_tax = ZERO
        cumulative_state_income_tax = ZERO
        cumulative_cap_gains_tax = ZERO
        cumulative_drag = ZERO
        yearly: list[YearlyRow] = []

        for year in range(horizon):
            # Beginning-of-year contribution.
            balance += annual_contribution
            cost_basis += annual_contribution
            contributions_to_date += annual_contribution

            # Gross investment return for the year (simple compounding).
            gross_growth = balance * r
            balance += gross_growth

            # Of the gross_growth, dividend_yield × prior_balance was paid as cash
            # distributions, the rest is unrealized appreciation. We approximate by
            # treating dividend_yield as a fraction of the total return.
            div_income = balance * dividend_yield / (D("1") + r)  # back into period-start basis
            qualified_div = div_income * qualified_fraction
            ordinary_div = div_income * (D("1") - qualified_fraction)

            # Realized gains from portfolio turnover (turnover × unrealized appreciation).
            unrealized = balance - cost_basis
            realized_gains = unrealized * turnover if unrealized > ZERO else ZERO
            lt_gains = realized_gains * lt_fraction
            st_gains = realized_gains * (D("1") - lt_fraction)

            # Adjust cost basis upward for realized gains (basis recovers as gains
            # are recognized; future sales then face less embedded gain).
            cost_basis += realized_gains

            # ----- federal tax on this year's income drag -----
            federal_ordinary_drag = (ordinary_div + st_gains) * ordinary_marginal
            federal_preferential_drag = (qualified_div + lt_gains) * ltcg_rate
            federal_niit_drag = (div_income + realized_gains) * niit_rate

            federal_income_drag = federal_ordinary_drag + federal_niit_drag
            federal_capgains_drag = federal_preferential_drag

            # ----- state tax on this year's income drag -----
            state_ord_drag = regime.state_income_tax(ordinary_div + st_gains, inputs).state_income_tax
            state_capgains_drag = regime.state_capital_gains_tax(qualified_div + lt_gains, inputs).state_income_tax
            state_income_drag_year = state_ord_drag + state_capgains_drag

            year_total_drag = (
                federal_income_drag
                + federal_capgains_drag
                + state_income_drag_year
            )

            # Drag is paid from the portfolio (assumption: investor uses portfolio
            # distributions to cover tax).
            balance -= year_total_drag

            cumulative_income_tax += federal_income_drag
            cumulative_cap_gains_tax += federal_capgains_drag
            cumulative_state_income_tax += state_income_drag_year
            cumulative_drag += year_total_drag

            yearly.append(YearlyRow(
                year_index=year,
                child_age=inputs.child_age + year,
                contributions_to_date=round_cents(contributions_to_date),
                pretax_balance=round_cents(balance),
                annual_tax_drag=round_cents(year_total_drag),
                cumulative_tax_drag=round_cents(cumulative_drag),
            ))

        pretax_terminal = balance

        # ----- §1014 step-up at donor's death -----
        # At death, basis steps up to FMV → embedded gain is forgiven.
        # Community-property double step-up: §1014(b)(6) gives BOTH halves of
        # community property a step-up, doubling the benefit for married TX donors
        # vs. an equivalent NY/IL couple.
        # (For an unmarried TX donor the double step-up does not apply.)

        cp_double_step_up = regime.is_community_property and inputs.spouse_present
        # The step-up itself doesn't show as a tax saving in cap-gains line —
        # it shows as the *absence* of further capital gains tax on the embedded
        # appreciation. We surface this in the assumptions/warnings list.

        # ----- federal estate tax -----
        gross_estate = D(inputs.donor_net_worth) + pretax_terminal
        # Simple MVP: assume the contribution-derived portfolio is *part of*
        # donor_net_worth at end of horizon (no double-count). We treat the
        # comparison as "this portfolio is the marginal slice being planned".
        # So gross_estate for *this* strategy's comparison is the terminal value
        # of the slice, plus the un-modified existing net worth that already
        # exists in any strategy.
        # To produce strategy-level comparability, we use pretax_terminal as the
        # marginal slice plus donor_net_worth as the inherited base; deductions
        # are applied at the gross level.
        marital_deduction = ZERO   # planning is to children — no marital
        charitable_deduction = gross_estate * D(inputs.charitable_bequest_pct)
        admin_debts_deduction = ZERO

        applicable_exclusion = ctx.applicable_exclusion_with_portability()
        taxable_estate = gross_estate - marital_deduction - charitable_deduction - admin_debts_deduction
        federal_estate_tax, fed_estate_cites = ctx.federal_estate_tax(
            taxable_estate=taxable_estate,
            applicable_exclusion=applicable_exclusion,
        )

        # Allocate federal estate tax pro-rata to this strategy's slice
        slice_share = (pretax_terminal / gross_estate) if gross_estate > ZERO else ZERO
        federal_estate_on_slice = federal_estate_tax * slice_share

        # ----- state estate tax -----
        state_estate_result = regime.state_estate_tax(
            gross_estate=gross_estate,
            marital_deduction=marital_deduction,
            charitable_deduction=charitable_deduction,
            admin_debts_deduction=admin_debts_deduction,
            inputs=inputs,
        )
        state_estate_on_slice = state_estate_result.state_estate_tax * slice_share

        # ----- after-tax to recipient -----
        # Step-up means recipient inherits at pretax_terminal as basis. Selling
        # immediately produces zero capital gains. So the §1014 path is:
        # heir receives pretax_terminal − federal_estate_tax_on_slice − state_estate_on_slice.
        after_tax_to_recipient = pretax_terminal - federal_estate_on_slice - state_estate_on_slice

        # ----- assemble result -----
        breakdown = self._empty_breakdown()
        breakdown["income"] = round_cents(cumulative_income_tax)
        breakdown["capital_gains"] = round_cents(cumulative_cap_gains_tax)
        breakdown["estate"] = round_cents(federal_estate_on_slice)
        breakdown["state_income"] = round_cents(cumulative_state_income_tax)
        breakdown["state_estate"] = round_cents(state_estate_on_slice)

        citations = [
            CITATIONS["step_up_basis"],
            CITATIONS["gross_estate"],
            CITATIONS["estate_rate_schedule"],
            CITATIONS["lifetime_exemption"],
            CITATIONS["capital_gains_rates"],
            CITATIONS["ordinary_rates"],
            *fed_estate_cites,
            *state_estate_result.citations,
        ]
        if cp_double_step_up:
            citations.append(CITATIONS["community_property_double_step_up"])
        if niit_rate > ZERO:
            citations.append(CITATIONS["niit"])

        assumptions = [
            f"Pre-tax return {r * 100:.2f}%/yr, dividend yield "
            f"{dividend_yield * 100:.2f}%/yr ({qualified_fraction * 100:.0f}% qualified), "
            f"turnover {turnover * 100:.0f}%/yr.",
            f"Donor's marginal ordinary federal rate ≈ {ordinary_marginal * 100:.1f}%; "
            f"LTCG/QDI rate {ltcg_rate * 100:.1f}%.",
            f"State income/capital-gains tax assessed per {regime.name} rules; "
            f"§1014 step-up applied at donor's death.",
            f"Recipient sells immediately after step-up — zero embedded gain realized.",
        ]
        if cp_double_step_up:
            assumptions.append(
                "Community-property double step-up under §1014(b)(6) applied — "
                "both halves of community property receive a basis adjustment at "
                "the first spouse's death (TX-specific advantage for married donors)."
            )

        warnings = list(state_estate_result.warnings)
        if niit_rate > ZERO:
            warnings.append("Net Investment Income Tax (§1411) applied — donor AGI exceeds threshold.")

        etr = self._effective_tax_rate(breakdown, contributions_to_date, pretax_terminal)

        return StrategyResult(
            strategy_name=self.name,
            contribution_total=round_cents(contributions_to_date),
            pretax_terminal_value=round_cents(pretax_terminal),
            taxes_paid_breakdown=breakdown,
            after_tax_wealth_to_recipient=round_cents(after_tax_to_recipient),
            effective_tax_rate=etr,
            year_by_year_projection=yearly,
            citations=citations,
            assumptions=assumptions,
            warnings=warnings,
        )
