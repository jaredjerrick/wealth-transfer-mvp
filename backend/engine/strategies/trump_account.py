"""Trump Account (OBBBA §70404) — federal-seed custodial investment account.

Established by the One Big Beautiful Bill Act, signed July 4, 2025. Mechanics
as enacted with conservative assumptions on Treasury-pending details:

  • $1,000 federal seed for U.S.-citizen children born 2025–2028 (one-time).
  • Up to $5,000/yr after-tax contribution from parents/employer combined.
  • Tax-deferred growth, restricted to broad-based U.S. equity index funds.
  • No access before age 18; distributions after 18 taxed as ordinary income
    on the earnings portion (basis is recovered tax-free).
  • Rollover to traditional or Roth IRA permitted after age 18.
  • Not includible in donor's gross estate; parent contributions are completed
    gifts under §2511 within the §2503(b) annual exclusion.

This is a hybrid of UGMA/UTMA (custodial), Traditional IRA (tax-deferred,
ordinary-income on distribution), and 529 (low-friction wrapper). The Trump
Account's distinguishing feature is the $1,000 federal seed for eligible
newborns — a non-displaceable windfall that materially shifts the math at
low contribution levels.

Treasury rulemaking is still maturing; users should confirm specific
provisions against current guidance.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..citations import CITATIONS, Citation
from ..inputs import DonorInputs
from ..regimes.base import StateRegime
from ..tax_context import D, ZERO, TaxContext, round_cents
from .base import Strategy, StrategyResult, YearlyRow
from .explain import build_tax_explanations
from ..inputs import VehicleKey


# Birth year window for the federal seed (per OBBBA pilot).
SEED_BIRTH_YEAR_START = 2025
SEED_BIRTH_YEAR_END = 2028
SEED_AMOUNT = D("1000")
PARENT_ANNUAL_CAP = D("5000")
ACCESS_AGE = 18


class TrumpAccountStrategy(Strategy):
    name = "Trump Account"

    def evaluate(
        self,
        ctx: TaxContext,
        regime: StateRegime,
        inputs: DonorInputs,
    ) -> StrategyResult:
        # Use the rules file's parameters directly so the strategy stays
        # data-driven if Treasury updates indexed amounts.
        ta = ctx.federal["trump_account"]
        seed_amount = D(ta["federal_seed_amount"]["value"])
        parent_cap = D(ta["annual_contribution_cap_parent"]["value"])
        seed_start = int(ta["federal_seed_eligibility_birth_years"]["start"])
        seed_end = int(ta["federal_seed_eligibility_birth_years"]["end"])
        access_age = int(ta["early_withdrawal_age"]["value"])

        annual_contribution_cap = min(
            D(inputs.annual_contribution),
            parent_cap,
        )

        horizon = inputs.investment_horizon_years
        r = D(inputs.expected_pretax_return)

        # ----- Federal seed eligibility -----
        # MVP rule: the seed applies if the child was born in the eligible window.
        # We don't have the child's literal birth year on the form — derive it
        # from `child_age` and the tax-year context.
        current_year = ctx.tax_year
        child_birth_year = current_year - inputs.child_age
        seed_eligible = seed_start <= child_birth_year <= seed_end

        # ----- Accumulation (tax-deferred) -----
        existing = D(inputs.existing_balances.get(VehicleKey.TRUMP, 0))
        balance = existing
        cost_basis = existing  # treat existing balance as fully basis-bearing
        contributions_to_date = ZERO

        if seed_eligible:
            balance += seed_amount
            # The $1,000 federal seed is a government program transfer, NOT a
            # parent gift. It does not count toward the parent annual cap and
            # is not a basis-bearing parent contribution. Modeling choice:
            # treat as zero basis from donor's perspective — its earnings AND
            # principal flow as ordinary income at distribution (since it was
            # never taxed at the parent level).

        warnings: list[str] = []
        if not seed_eligible:
            warnings.append(
                f"Federal seed NOT applied — child birth year ({child_birth_year}) is outside "
                f"the OBBBA pilot window ({seed_start}–{seed_end}). Strategy still works, "
                f"just without the $1,000 windfall."
            )

        yearly: list[YearlyRow] = []
        for year in range(horizon):
            balance += annual_contribution_cap
            cost_basis += annual_contribution_cap
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

        # ----- Access-age constraint -----
        # If the horizon ends before the child turns 18, the corpus is locked.
        # We still report it as the pretax terminal but warn.
        child_age_at_terminal = inputs.child_age + horizon
        if child_age_at_terminal < access_age:
            warnings.append(
                f"At end of horizon child is age {child_age_at_terminal}, below the "
                f"§70404(f) access age ({access_age}). Distributions cannot begin yet — "
                f"corpus would need to remain in the account or roll to an IRA."
            )

        # ----- Distribution tax treatment -----
        # Earnings portion taxed at the BENEFICIARY's ordinary rate. We use the
        # 12% bracket as a reasonable proxy for an 18-year-old's first taxable
        # year, since the form doesn't collect the beneficiary's future income.
        # The user can adjust this assumption easily by editing the rules file.
        earnings_portion = pretax_terminal - cost_basis  # cost_basis here = parent contributions only
        # The federal seed (and its growth) is also taxable since it was never
        # taxed at the parent level — but we still treat the entire balance net
        # of parent contributions as taxable earnings, which is the right
        # accounting (the seed itself is ordinary income at distribution).

        BENEFICIARY_MARGINAL = D("0.12")
        federal_income_tax_on_distribution = earnings_portion * BENEFICIARY_MARGINAL

        # State income tax on distribution — uses the donor's state as a proxy
        # for the recipient's state.
        state_tax_on_distribution = regime.state_income_tax(earnings_portion, inputs).state_income_tax

        after_tax_to_recipient = (
            pretax_terminal
            - federal_income_tax_on_distribution
            - state_tax_on_distribution
        )

        breakdown = self._empty_breakdown()
        breakdown["income"] = round_cents(federal_income_tax_on_distribution)
        breakdown["state_income"] = round_cents(state_tax_on_distribution)

        citations = [
            CITATIONS["trump_account_act"],
            CITATIONS["trump_account_parent_cap"],
            CITATIONS["trump_account_distribution"],
            CITATIONS["trump_account_investment_restriction"],
            CITATIONS["completed_gift"],
            CITATIONS["annual_exclusion"],
        ]
        if seed_eligible:
            citations.insert(1, CITATIONS["trump_account_federal_seed"])
        if child_age_at_terminal >= access_age:
            citations.append(CITATIONS["trump_account_rollover"])

        assumptions = [
            f"Annual parent contribution capped at min(${inputs.annual_contribution:,.0f}, "
            f"${parent_cap:,.0f}) = ${annual_contribution_cap:,.0f}. Not deductible (after-tax).",
            f"Federal $1,000 seed: child born {child_birth_year} → "
            f"{'eligible (added at year 0)' if seed_eligible else 'NOT eligible (outside 2025–2028 window)'}.",
            "Tax-deferred growth; investments restricted to broad-based U.S. equity index funds. "
            "Default return rate applied (no asset-class adjustment in MVP).",
            f"Distribution at age {access_age}+ taxed as ordinary income on the earnings portion. "
            f"Beneficiary marginal rate proxied at {BENEFICIARY_MARGINAL * 100:.0f}% federal.",
            "Asset is NOT includible in donor's gross estate. Parent contributions are completed "
            "gifts (§2511) within the $19,000 annual exclusion.",
            "Account may be rolled to a traditional or Roth IRA after age 18 (§70404(h)) — "
            "MVP reports pre-rollover terminal value.",
            "Treasury implementing regulations were still being issued at the time of modeling; "
            "specific provisions should be confirmed against current guidance.",
        ]

        if D(inputs.annual_contribution) > parent_cap:
            warnings.append(
                f"Annual contribution input (${inputs.annual_contribution:,.0f}) exceeds the "
                f"§70404(c)(1) parent cap (${parent_cap:,.0f}). Capped at the statutory limit; "
                f"excess assumed redirected to another vehicle (not modeled in this strategy's corpus)."
            )

        if existing > ZERO:
            assumptions.append(
                f"Starting corpus: ${existing:,.0f} of existing Trump Account balance seeded at year 0."
            )

        rationales = {
            "income": (
                f"Ordinary income tax on the earnings portion at the beneficiary's marginal rate "
                f"(proxied at {BENEFICIARY_MARGINAL * 100:.0f}% in MVP) under OBBBA §70404(g)."
            ),
            "state_income": f"{regime.name} state income tax on the earnings portion of the distribution.",
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
