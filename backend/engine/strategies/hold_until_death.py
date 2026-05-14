"""Hold-Until-Death — donor retains assets, transferring at death to maximize §1014 step-up.

Distinguishing characteristic vs. Taxable Brokerage: this strategy assumes the
donor reinvests dividends and minimizes realized gains (long-term buy-and-hold).
Tax drag during accumulation is therefore much lower than the brokerage default
(turnover = 0 in MVP), at the cost of less liquidity along the way.

Key levers:
  - §1014 step-up at death (community-property double step-up for TX married).
  - §2010 unified credit + §2010(c)(2)(B) portability for married couples.
  - §2056 marital deduction (modeled at 0 here — bequest is to children).
  - §2055 charitable deduction (if user supplied charitable_bequest_pct > 0).
  - §2053 administration/debts deduction (out of MVP — assumed zero).
  - NY estate cliff applies via the state regime.
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


class HoldUntilDeathStrategy(Strategy):
    name = "Hold Until Death"

    def evaluate(
        self,
        ctx: TaxContext,
        regime: StateRegime,
        inputs: DonorInputs,
    ) -> StrategyResult:
        annual_contribution = D(inputs.annual_contribution)
        horizon = inputs.investment_horizon_years
        r = D(inputs.expected_pretax_return)
        # Minimal dividend tax drag — buy-and-hold; assume only unavoidable
        # qualified dividend distributions occur.
        dividend_yield = D(ctx.defaults["dividend_yield"]) * D("0.5")  # half default — index-fund-like

        donor_agi = D(inputs.donor_gross_income_agi)
        ltcg_rate = ctx.federal_ltcg_rate(donor_agi)
        niit_rate = ctx.niit_rate_applies(donor_agi)

        existing = D(inputs.existing_balances.get(VehicleKey.HOLD, 0))
        balance = existing
        contributions_to_date = ZERO
        cumulative_drag = ZERO
        cumulative_cap_gains_tax = ZERO
        cumulative_state_income_tax = ZERO
        yearly: list[YearlyRow] = []

        for year in range(horizon):
            balance += annual_contribution
            contributions_to_date += annual_contribution
            gross_growth = balance * r
            balance += gross_growth

            div_income = balance * dividend_yield / (D("1") + r)
            federal_drag = div_income * ltcg_rate + div_income * niit_rate
            state_drag = regime.state_capital_gains_tax(div_income, inputs).state_income_tax
            year_drag = federal_drag + state_drag
            balance -= year_drag

            cumulative_cap_gains_tax += federal_drag - (div_income * niit_rate)
            cumulative_state_income_tax += state_drag
            cumulative_drag += year_drag

            yearly.append(YearlyRow(
                year_index=year,
                child_age=inputs.child_age + year,
                contributions_to_date=round_cents(contributions_to_date),
                pretax_balance=round_cents(balance),
                annual_tax_drag=round_cents(year_drag),
                cumulative_tax_drag=round_cents(cumulative_drag),
            ))

        pretax_terminal = balance

        # §1014 step-up at death → embedded gain forgiven for the heir.
        # Estate inclusion: federal + state.
        gross_estate = D(inputs.donor_net_worth) + pretax_terminal
        charitable_deduction = gross_estate * D(inputs.charitable_bequest_pct)
        marital_deduction = ZERO
        admin_debts_deduction = ZERO

        applicable_exclusion = ctx.applicable_exclusion_with_portability()
        taxable_estate = gross_estate - marital_deduction - charitable_deduction - admin_debts_deduction
        federal_estate_tax, fed_estate_cites = ctx.federal_estate_tax(
            taxable_estate=taxable_estate,
            applicable_exclusion=applicable_exclusion,
        )

        slice_share = (pretax_terminal / gross_estate) if gross_estate > ZERO else ZERO
        federal_estate_on_slice = federal_estate_tax * slice_share

        state_estate_result = regime.state_estate_tax(
            gross_estate=gross_estate,
            marital_deduction=marital_deduction,
            charitable_deduction=charitable_deduction,
            admin_debts_deduction=admin_debts_deduction,
            inputs=inputs,
        )
        state_estate_on_slice = state_estate_result.state_estate_tax * slice_share

        # GST overlay if the recipient is a skip person.
        gst_on_slice = ZERO
        gst_cites: list = []
        if inputs.elect_skip_generation:
            net_after_estate = pretax_terminal - federal_estate_on_slice - state_estate_on_slice
            gst_on_slice, _, gst_cites = ctx.apply_gst(net_after_estate)

        after_tax_to_recipient = (
            pretax_terminal - federal_estate_on_slice - state_estate_on_slice - gst_on_slice
        )

        breakdown = self._empty_breakdown()
        breakdown["capital_gains"] = round_cents(cumulative_cap_gains_tax)
        breakdown["state_income"] = round_cents(cumulative_state_income_tax)
        breakdown["estate"] = round_cents(federal_estate_on_slice)
        breakdown["gst"] = round_cents(gst_on_slice)
        breakdown["state_estate"] = round_cents(state_estate_on_slice)

        citations = [
            CITATIONS["step_up_basis"],
            CITATIONS["gross_estate"],
            CITATIONS["estate_rate_schedule"],
            CITATIONS["lifetime_exemption"],
            CITATIONS["portability_dsue"],
            *fed_estate_cites,
            *state_estate_result.citations,
        ]
        if regime.is_community_property and inputs.spouse_present:
            citations.append(CITATIONS["community_property_double_step_up"])
        if gst_on_slice > ZERO:
            citations.extend(gst_cites)

        assumptions = [
            "Buy-and-hold portfolio; portfolio turnover ≈ 0 — minimal realized gains during accumulation.",
            f"§1014 step-up forgives all embedded gain at donor's death.",
            f"DSUE portability assumed elected for married donors; applicable exclusion = "
            f"${applicable_exclusion:,.0f}.",
            f"Charitable bequest fraction = {D(inputs.charitable_bequest_pct) * 100:.1f}% "
            f"(deductible under §2055).",
        ]
        warnings = list(state_estate_result.warnings)

        rationales = {
            "capital_gains": "Minimal qualified-dividend drag during buy-and-hold accumulation; turnover ≈ 0.",
            "state_income": f"{regime.name} tax on the small dividend stream.",
            "estate": (
                f"Pro-rata slice of the federal estate tax on a taxable estate of "
                f"${round_cents(taxable_estate):,.0f}, after §2010 unified credit "
                f"(${applicable_exclusion:,.0f}). The §1014 step-up forgives embedded gains but "
                f"the corpus itself is still includible in the gross estate."
            ),
            "state_estate": f"Pro-rata slice of the {regime.name} state estate tax.",
            "gst": (
                f"Generation-skipping transfer tax at {ctx.gst_top_rate * 100:.0f}% on the portion of "
                f"the transfer exceeding the remaining §2631 GST exemption "
                f"(${ctx.gst_exemption:,.0f} for 2025)."
            ),
        }

        if existing > ZERO:
            assumptions.append(
                f"Starting corpus: ${existing:,.0f} of existing hold-until-death holdings seeded at year 0."
            )
        if inputs.elect_skip_generation:
            assumptions.append("Recipient designated as a skip person — GST tax (§§2611, 2631, 2641) applied.")

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
