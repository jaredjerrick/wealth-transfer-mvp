"""Abstract base class for state regimes.

The calculation engine never reaches inside the state dict directly — it talks
to a `StateRegime` instance. This is the single seam where state-specific
numbers live.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from ..citations import Citation
from ..inputs import DonorInputs, FilingStatus
from ..tax_context import D, ZERO, progressive_tax, flat_bracket_rate


@dataclass
class StateEstateResult:
    state_estate_tax: Decimal
    cliff_triggered: bool
    citations: list[Citation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class StateIncomeTaxResult:
    state_income_tax: Decimal
    citations: list[Citation] = field(default_factory=list)


class StateRegime(ABC):
    """Interface every state regime must implement."""

    code: str
    name: str

    def __init__(self, rules: dict):
        self.rules = rules
        self.state_data = rules["states"][self.code]

    # ----- income tax -----

    @abstractmethod
    def state_income_tax(self, taxable_income: Decimal, inputs: DonorInputs) -> StateIncomeTaxResult: ...

    @abstractmethod
    def state_capital_gains_tax(self, ltcg: Decimal, inputs: DonorInputs) -> StateIncomeTaxResult:
        """For most states this aliases to ordinary income tax; preference for cap gains
        is a federal phenomenon. NY and IL both tax cap gains as ordinary."""

    # ----- 529 deduction -----

    @abstractmethod
    def section_529_deduction(self, contribution: Decimal, inputs: DonorInputs) -> tuple[Decimal, list[Citation]]:
        """Returns the (deductible amount, citations) for a 529 contribution.

        Deductions in excess of the annual cap are lost in MVP (some states allow
        carryforward — schema reserves this for later)."""

    # ----- estate tax -----

    @abstractmethod
    def state_estate_tax(
        self,
        gross_estate: Decimal,
        marital_deduction: Decimal,
        charitable_deduction: Decimal,
        admin_debts_deduction: Decimal,
        inputs: DonorInputs,
    ) -> StateEstateResult: ...

    # ----- structural flags -----

    @property
    def is_community_property(self) -> bool:
        return bool(self.state_data.get("community_property", False))

    @property
    def utma_age_of_majority(self) -> int:
        return int(self.state_data.get("utma_age_of_majority", 21))
