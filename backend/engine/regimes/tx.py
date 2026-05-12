"""Texas state regime.

No state income tax (Tex. Const. art. VIII §24-a), no state estate or
inheritance tax, and a community property regime that produces the §1014(b)(6)
double step-up on death of the first spouse — a meaningful planning advantage
for married Texas donors holding appreciated assets.
"""

from __future__ import annotations

from decimal import Decimal

from ..citations import Citation, CITATIONS
from ..inputs import DonorInputs
from ..tax_context import D, ZERO
from .base import StateRegime, StateEstateResult, StateIncomeTaxResult


class TXRegime(StateRegime):
    code = "TX"
    name = "Texas"

    def state_income_tax(self, taxable_income: Decimal, inputs: DonorInputs) -> StateIncomeTaxResult:
        return StateIncomeTaxResult(
            state_income_tax=ZERO,
            citations=[CITATIONS["tx_no_income_tax"]],
        )

    def state_capital_gains_tax(self, ltcg: Decimal, inputs: DonorInputs) -> StateIncomeTaxResult:
        return self.state_income_tax(ltcg, inputs)

    def section_529_deduction(
        self,
        contribution: Decimal,
        inputs: DonorInputs,
    ) -> tuple[Decimal, list[Citation]]:
        # No state income tax base → no deduction.
        return ZERO, [CITATIONS["tx_no_income_tax"]]

    def state_estate_tax(
        self,
        gross_estate: Decimal,
        marital_deduction: Decimal,
        charitable_deduction: Decimal,
        admin_debts_deduction: Decimal,
        inputs: DonorInputs,
    ) -> StateEstateResult:
        return StateEstateResult(
            state_estate_tax=ZERO,
            cliff_triggered=False,
            citations=[CITATIONS["tx_no_estate_tax"]],
        )
