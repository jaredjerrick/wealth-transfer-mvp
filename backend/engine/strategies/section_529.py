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

**Contribution caps enforced (added per product feedback):**
  - **§529(b)(7) adequate-safeguards:** each state plan enforces an aggregate
    per-beneficiary contribution limit (NY $520K, IL $500K, TX $500K). Once
    cumulative contributions reach this cap, the engine stops adding new
    dollars to corpus (corpus continues to grow tax-free).
  - **Age-22 cutoff:** the engine assumes no further contributions after the
    beneficiary turns 22 (typical undergrad completion). This is a planning
    assumption layered on top of §529(b)(7), not a federal rule. SECURE 2.0
    §126 Roth-rollover handles residual corpus.
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


class Section529Strategy(Strategy):
    name = "529 Plan"

    def evaluate(
        self,
        ctx: TaxContext,
        regime: StateRegime,
        inputs: DonorInputs,
    ) -> StrategyResult:
        annual_contribution_requested = D(inputs.annual_contribution)
        horizon = inputs.investment_horizon_years
        r = D(inputs.expected_pretax_return)

        # ----- contribution-cap parameters -----
        age_cutoff = int(ctx.federal["section_529"]["default_contribution_age_cutoff"]["value"])
        aggregate_cap = regime.section_529_aggregate_cap

        # ----- Gift-tax handling -----
        # 5-year election lets donor frontload up to 5× the annual exclusion
        # in year one. Tracked separately to surface in citations and
        # assumptions; the MVP does not deplete lifetime exemption unless the
        # contribution is large.
        annual_exclusion = ctx.annual_exclusion_total(num_donees=1)
        cites_gift: list = [CITATIONS["annual_exclusion"], CITATIONS["completed_gift"]]
        if inputs.elect_529_five_year and annual_contribution_requested > annual_exclusion:
            cites_gift.append(CITATIONS["five_year_election_529"])

        # ----- State income tax deduction (benefit calculated at donor's marginal) -----
        state_deductible, state_ded_cites = regime.section_529_deduction(annual_contribution_requested, inputs)
        # Approximate state benefit = deductible × state marginal income rate.
        if regime.code == "IL":
            state_marginal = D(regime.state_data["income_tax"]["flat_rate"])
        elif regime.code == "TX":
            state_marginal = ZERO
        else:  # NY
            agi_state_tax = regime.state_income_tax(D(inputs.donor_gross_income_agi), inputs).state_income_tax
            state_marginal = (agi_state_tax / D(inputs.donor_gross_income_agi)) if D(inputs.donor_gross_income_agi) > ZERO else ZERO

        # ----- Accumulation (tax-free), with cap enforcement -----
        # Seed existing 529 balance, if any.
        existing = D(inputs.existing_balances.get(VehicleKey.SEC_529, 0))
        balance = existing
        cumulative_contributions = ZERO
        cumulative_state_benefit = ZERO
        yearly: list[YearlyRow] = []
        warnings: list[str] = []

        age_cap_hit_year: int | None = None
        aggregate_cap_hit_year: int | None = None

        for year in range(horizon):
            child_age_this_year = inputs.child_age + year

            # --- Determine this year's actual contribution ---
            this_year_contribution = ZERO

            if child_age_this_year > age_cutoff:
                # Age-based cutoff binds.
                if age_cap_hit_year is None:
                    age_cap_hit_year = year
                    warnings.append(
                        f"529 contributions stop at end of year {year}: beneficiary turns "
                        f"{age_cutoff + 1}, past the default age-{age_cutoff} education-funding "
                        f"window. Corpus continues to grow tax-free."
                    )
            elif cumulative_contributions >= aggregate_cap:
                # Aggregate state cap binds.
                if aggregate_cap_hit_year is None:
                    aggregate_cap_hit_year = year
                    warnings.append(
                        f"§529(b)(7) aggregate cap reached in year {year}: cumulative "
                        f"contributions of ${cumulative_contributions:,.0f} have hit the "
                        f"{regime.name} aggregate per-beneficiary limit of "
                        f"${aggregate_cap:,.0f}. No further contributions accepted; corpus "
                        f"continues to grow tax-free."
                    )
            else:
                # Contribution is allowed — but the aggregate cap may partially bind
                # this year (we top up to the cap and no more).
                remaining_room = aggregate_cap - cumulative_contributions
                this_year_contribution = min(annual_contribution_requested, remaining_room)
                if this_year_contribution < annual_contribution_requested:
                    # The cap binds *partway* through this year.
                    if aggregate_cap_hit_year is None:
                        aggregate_cap_hit_year = year
                        warnings.append(
                            f"§529(b)(7) aggregate cap partially binds in year {year}: only "
                            f"${this_year_contribution:,.0f} of the requested "
                            f"${annual_contribution_requested:,.0f} contribution is accepted "
                            f"before hitting the {regime.name} cap of ${aggregate_cap:,.0f}."
                        )

            balance += this_year_contribution
            cumulative_contributions += this_year_contribution
            balance += balance * r  # tax-free growth

            # State income-tax deduction only applies to the deductible portion of
            # *actual* contributions this year, capped at the state deduction limit.
            deductible_this_year = min(this_year_contribution, state_deductible)
            year_state_benefit = deductible_this_year * state_marginal
            cumulative_state_benefit += year_state_benefit

            yearly.append(YearlyRow(
                year_index=year,
                child_age=child_age_this_year,
                contributions_to_date=round_cents(cumulative_contributions),
                pretax_balance=round_cents(balance),
                annual_tax_drag=ZERO,
                cumulative_tax_drag=round_cents(-cumulative_state_benefit),  # negative = benefit
            ))

        pretax_terminal = balance
        # Qualified distributions are tax-free → after-tax to recipient = pretax_terminal.

        breakdown = self._empty_breakdown()
        breakdown["state_income"] = round_cents(-cumulative_state_benefit)  # negative = saved

        after_tax_to_recipient = pretax_terminal

        citations = [
            CITATIONS["529_growth"],
            CITATIONS["529_qualified_distribution"],
            CITATIONS["529_estate_exclusion"],
            CITATIONS["529_adequate_safeguards"],
            CITATIONS["529_aggregate_cap_state"],
            CITATIONS["annual_exclusion"],
            *cites_gift,
            *state_ded_cites,
        ]

        assumptions = [
            "Beneficiary uses corpus for qualified education expenses — distributions are federal-tax-free under §529(c)(3).",
            f"State income-tax deduction capped at deductible amount × state marginal rate "
            f"(${state_deductible:,.0f}/yr deductible while contributions are active).",
            "Corpus excluded from donor's gross estate under §529(c)(4).",
            f"Contributions stop at the earlier of (i) beneficiary age {age_cutoff} "
            f"(end of typical undergrad), or (ii) aggregate per-beneficiary cap of "
            f"${aggregate_cap:,.0f} for {regime.name}. §529(b)(7) requires the plan to "
            f"prevent contributions exceeding qualified education expenses.",
            "SECURE 2.0 §126: up to $35,000 lifetime may be rolled to a Roth IRA for the beneficiary (subject to 15-year account age and annual IRA limits).",
        ]
        if inputs.elect_529_five_year:
            assumptions.append(
                f"5-year forward election (§529(c)(2)(B)) elected — year 1 gift treated "
                f"as made ratably over 5 years for annual exclusion purposes."
            )
        if existing > ZERO:
            assumptions.append(
                f"Starting corpus: ${existing:,.0f} of existing 529 balance seeded at year 0; "
                f"continues compounding tax-free under §529(c)(1)."
            )
        if inputs.elect_skip_generation:
            assumptions.append(
                "Direct-skip 529 gifts to a grandchild qualify for the §2503(b) annual exclusion "
                "and can be sheltered by GST exemption allocation under §2632 — MVP treats these "
                "as fully sheltered, so no incremental GST tax is shown."
            )

        if annual_contribution_requested > annual_exclusion and not inputs.elect_529_five_year:
            warnings.append(
                f"Annual contribution ${annual_contribution_requested:,.0f} exceeds annual "
                f"exclusion ${annual_exclusion:,.0f}. Consider electing the §529(c)(2)(B) "
                f"five-year forward election to avoid using lifetime exemption."
            )

        rationales = {
            "state_income": (
                f"Negative number = state income-tax benefit. The {regime.name} 529 deduction "
                f"(cap ${state_deductible:,.0f}/yr while contributions are active) saves the "
                f"donor approximately {state_marginal * 100:.2f}% of each deductible dollar."
            ),
        }

        return StrategyResult(
            strategy_name=self.name,
            contribution_total=round_cents(cumulative_contributions),
            pretax_terminal_value=round_cents(pretax_terminal),
            taxes_paid_breakdown=breakdown,
            after_tax_wealth_to_recipient=round_cents(after_tax_to_recipient),
            effective_tax_rate=self._effective_tax_rate(breakdown, cumulative_contributions, pretax_terminal),
            year_by_year_projection=yearly,
            citations=citations,
            assumptions=assumptions,
            warnings=warnings,
            tax_explanations=build_tax_explanations(breakdown, rationales),
        )
