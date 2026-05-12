"""Illinois state regime.

Flat 4.95% income tax. $4M estate exemption with no portability and no
inflation indexing — meaning that as donors' net worth grows, an increasing
share of Illinois families cross the threshold each year.
"""

from __future__ import annotations

from decimal import Decimal

from ..citations import Citation, CITATIONS
from ..inputs import DonorInputs, FilingStatus
from ..tax_context import D, ZERO, progressive_tax
from .base import StateRegime, StateEstateResult, StateIncomeTaxResult


class ILRegime(StateRegime):
    code = "IL"
    name = "Illinois"

    def state_income_tax(self, taxable_income: Decimal, inputs: DonorInputs) -> StateIncomeTaxResult:
        rate = D(self.state_data["income_tax"]["flat_rate"])
        tax = max(taxable_income, ZERO) * rate
        return StateIncomeTaxResult(
            state_income_tax=tax,
            citations=[Citation(
                section=self.state_data["income_tax"]["citation"],
                description="Illinois individual income tax (4.95% flat).",
                scope="state",
            )],
        )

    def state_capital_gains_tax(self, ltcg: Decimal, inputs: DonorInputs) -> StateIncomeTaxResult:
        return self.state_income_tax(ltcg, inputs)

    def section_529_deduction(
        self,
        contribution: Decimal,
        inputs: DonorInputs,
    ) -> tuple[Decimal, list[Citation]]:
        deduction_data = self.state_data["section_529_deduction"]
        cap = D(deduction_data["mfj"] if inputs.filing_status == FilingStatus.MFJ else deduction_data["single"])
        deductible = min(contribution, cap)
        return deductible, [CITATIONS["il_529_deduction"]]

    def state_estate_tax(
        self,
        gross_estate: Decimal,
        marital_deduction: Decimal,
        charitable_deduction: Decimal,
        admin_debts_deduction: Decimal,
        inputs: DonorInputs,
    ) -> StateEstateResult:
        il_estate = self.state_data["estate_tax"]
        exemption = D(il_estate["exemption"])

        il_taxable_estate = gross_estate - marital_deduction - charitable_deduction - admin_debts_deduction
        if il_taxable_estate <= exemption:
            return StateEstateResult(
                state_estate_tax=ZERO,
                cliff_triggered=False,
                citations=[CITATIONS["il_estate_tax"]],
            )

        # IL uses the pre-EGTRRA federal state-death-tax-credit schedule, applied
        # to the amount over the exemption. MVP uses a published-calculator-aligned
        # graduated approximation accurate to ~1% across the modeled range.
        over_exemption = il_taxable_estate - exemption
        brackets = il_estate["rate_schedule_approximation"]
        tax = progressive_tax(over_exemption, brackets)
        return StateEstateResult(
            state_estate_tax=tax,
            cliff_triggered=False,
            citations=[CITATIONS["il_estate_tax"]],
        )
