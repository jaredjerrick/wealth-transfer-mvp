"""New York state regime.

The defining quirk: NY estate tax has a 'cliff' at 105% of the basic exclusion
amount. If the NY taxable estate exceeds 1.05 × $7.35M = $7.7175M (2026),
the entire estate is taxed at the §952 rate schedule with NO exemption credit.
The MVP models this discontinuity explicitly because it is the single largest
state-tax planning trap for affluent New York families.
"""

from __future__ import annotations

from decimal import Decimal

from ..citations import Citation, CITATIONS
from ..inputs import DonorInputs, FilingStatus
from ..tax_context import D, ZERO, progressive_tax, flat_bracket_rate
from .base import StateRegime, StateEstateResult, StateIncomeTaxResult


class NYRegime(StateRegime):
    code = "NY"
    name = "New York"

    def state_income_tax(self, taxable_income: Decimal, inputs: DonorInputs) -> StateIncomeTaxResult:
        brackets = self.state_data["income_tax"][inputs.filing_status.value]
        tax = progressive_tax(taxable_income, brackets)

        cites = [Citation(
            section=self.state_data["income_tax"]["citation"],
            description="New York individual income tax (graduated).",
            scope="state",
        )]

        if inputs.nyc_resident:
            # MVP simplification: apply NYC top marginal rate as a flat add-on.
            # Production would carry the full city bracket schedule.
            nyc_rate = D(self.state_data["nyc_income_tax_top_rate"]["value"])
            tax += taxable_income * nyc_rate
            cites.append(Citation(
                section=self.state_data["nyc_income_tax_top_rate"]["citation"],
                description="NYC resident income tax (top marginal rate applied as flat add-on).",
                scope="state",
            ))
        return StateIncomeTaxResult(state_income_tax=tax, citations=cites)

    def state_capital_gains_tax(self, ltcg: Decimal, inputs: DonorInputs) -> StateIncomeTaxResult:
        # NY taxes long-term capital gains as ordinary income.
        return self.state_income_tax(ltcg, inputs)

    def section_529_deduction(
        self,
        contribution: Decimal,
        inputs: DonorInputs,
    ) -> tuple[Decimal, list[Citation]]:
        deduction_data = self.state_data["section_529_deduction"]
        cap = D(deduction_data["mfj"] if inputs.filing_status == FilingStatus.MFJ else deduction_data["single"])
        deductible = min(contribution, cap)
        return deductible, [CITATIONS["ny_529_deduction"]]

    def state_estate_tax(
        self,
        gross_estate: Decimal,
        marital_deduction: Decimal,
        charitable_deduction: Decimal,
        admin_debts_deduction: Decimal,
        inputs: DonorInputs,
    ) -> StateEstateResult:
        ny_estate = self.state_data["estate_tax"]
        exemption = D(ny_estate["exemption"])
        cliff_multiplier = D(ny_estate["cliff_threshold_multiplier"])

        ny_taxable_estate = gross_estate - marital_deduction - charitable_deduction - admin_debts_deduction
        if ny_taxable_estate <= ZERO:
            return StateEstateResult(
                state_estate_tax=ZERO,
                cliff_triggered=False,
                citations=[CITATIONS["ny_estate_cliff"]],
            )

        cites = [CITATIONS["ny_estate_cliff"]]
        warnings: list[str] = []

        cliff_threshold = exemption * cliff_multiplier  # 1.05 × NY BEA (e.g. $7.7175M for 2026)
        brackets = ny_estate["rate_schedule"]

        if ny_taxable_estate <= exemption:
            # Under the exemption — no NY estate tax.
            return StateEstateResult(
                state_estate_tax=ZERO,
                cliff_triggered=False,
                citations=cites,
            )

        if ny_taxable_estate >= cliff_threshold:
            # Cliff fully triggered — tax the ENTIRE estate (no exemption credit).
            tax = progressive_tax(ny_taxable_estate, brackets)
            warnings.append(
                f"NY estate cliff triggered: taxable estate of ${ny_taxable_estate:,.0f} "
                f"exceeds 105% threshold (${cliff_threshold:,.0f}). Entire estate is "
                f"taxable with NO exemption credit."
            )
            return StateEstateResult(
                state_estate_tax=tax,
                cliff_triggered=True,
                citations=cites,
                warnings=warnings,
            )

        # In the cliff phase-out zone (exemption < taxable_estate < 105% × exemption).
        # NY phases out the exemption credit linearly over this $358K window.
        # Effective formula: tax = full_schedule_tax × (taxable - exemption) / (cliff - exemption)
        # ...but only when that produces a number larger than the pure-schedule-above-exemption tax.
        # In practice this produces a brutal marginal rate inside the phase-out window.
        full_tax = progressive_tax(ny_taxable_estate, brackets)
        over = ny_taxable_estate - exemption
        window = cliff_threshold - exemption
        phased_credit = (D("1") - (over / window)) * full_tax
        tax_in_phase_out = full_tax - phased_credit
        warnings.append(
            f"NY estate exemption phasing out: taxable estate of ${ny_taxable_estate:,.0f} "
            f"is in the cliff window (${exemption:,.0f}–${cliff_threshold:,.0f}). "
            f"Effective marginal rate is significantly elevated."
        )
        return StateEstateResult(
            state_estate_tax=tax_in_phase_out,
            cliff_triggered=False,
            citations=cites,
            warnings=warnings,
        )
