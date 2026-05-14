"""User input schema for the calculation engine.

Pydantic models that the FastAPI layer validates. Validation is duplicated
client-side, but the engine treats the API boundary as untrusted: an invalid
payload here must produce an HTTP 400 with the precise authority citation
explaining the rejection (e.g., a Roth contribution with no earned income
returns a §219(b) / §408A(c) hard block).
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class FilingStatus(str, Enum):
    SINGLE = "single"
    MFJ = "mfj"
    MFS = "mfs"
    HOH = "hoh"


class StateCode(str, Enum):
    NY = "NY"
    IL = "IL"
    TX = "TX"


class MortalityModel(str, Enum):
    DETERMINISTIC = "deterministic"  # donor dies at end of horizon
    ACTUARIAL = "actuarial"          # SSA life-table probability weighting


class VehicleKey(str, Enum):
    """Canonical machine keys for each modeled vehicle. Kept in sync with the
    `Strategy.name` registered in `engine.strategies.__init__.ALL_STRATEGIES`."""
    TAXABLE = "taxable_brokerage"
    HOLD = "hold_until_death"
    SEC_529 = "section_529"
    UGMA = "ugma_utma"
    TRAD_IRA = "traditional_ira"
    ROTH_IRA = "roth_ira"
    TRUMP = "trump_account"


class AllocationItem(BaseModel):
    """One row of a diversified-portfolio allocation: vehicle + annual dollars."""
    vehicle: VehicleKey
    annual_amount: Decimal = Field(ge=0, le=Decimal("1000000"))


class DonorInputs(BaseModel):
    """The form payload. All monetary fields are USD; decimals are fractions."""

    # Donor profile
    donor_age: int = Field(ge=18, le=110)
    donor_gross_income_agi: Decimal = Field(ge=0, le=Decimal("10000000"))
    filing_status: FilingStatus
    state: StateCode
    nyc_resident: bool = False
    donor_net_worth: Decimal = Field(ge=0, le=Decimal("1000000000"))
    spouse_present: bool = False
    num_children: int = Field(default=1, ge=1, le=10)
    planned_retirement_age: Optional[int] = Field(default=None, ge=40, le=85)

    # Child / beneficiary profile
    child_age: int = Field(ge=0, le=25)
    child_earned_income: Decimal = Field(default=Decimal("0"), ge=0)
    child_expects_college: bool = True
    # Existing balances in each vehicle (machine-key -> dollars). Optional;
    # an empty dict means "starts from zero in every vehicle".
    existing_balances: Dict[VehicleKey, Decimal] = Field(default_factory=dict)

    # Planning horizon and contributions
    investment_horizon_years: int = Field(ge=1, le=60)
    annual_contribution: Decimal = Field(ge=0, le=Decimal("1000000"))

    # Optional diversified allocation. If provided AND non-empty, the engine
    # also produces a "Diversified Portfolio" composite strategy.
    allocation: Optional[List[AllocationItem]] = None

    # Economic assumptions
    expected_pretax_return: Decimal = Field(default=Decimal("0.07"), ge=Decimal("-0.20"), le=Decimal("0.30"))
    inflation_rate: Decimal = Field(default=Decimal("0.025"), ge=Decimal("-0.05"), le=Decimal("0.15"))

    # Modeling toggles
    mortality_model: MortalityModel = MortalityModel.DETERMINISTIC
    tax_year: int = Field(default=2025, ge=2025, le=2030)
    elect_529_five_year: bool = False
    elect_gift_splitting: bool = False  # requires spouse_present = True
    charitable_bequest_pct: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("1"))

    # ---- Generation-skipping toggle (IRC §§2611, 2631, 2641) ----
    # When True, the engine treats the ultimate recipient as a "skip person"
    # (grandchild or later) and applies the GST tax on top of the gift /
    # estate tax for non-exempt strategies.
    elect_skip_generation: bool = False

    # ---- Life-event planning prompts ----
    plan_pay_college: bool = True       # Q: do you plan to pay for your child's college?
    plan_pay_wedding: bool = False      # Q: do you plan to pay for their wedding?
    plan_pay_first_home: bool = False   # Q: do you plan to help with a first home?
    est_college_cost_today: Decimal = Field(default=Decimal("150000"), ge=0, le=Decimal("2000000"))
    est_wedding_cost_today: Decimal = Field(default=Decimal("35000"), ge=0, le=Decimal("1000000"))
    est_first_home_help_today: Decimal = Field(default=Decimal("75000"), ge=0, le=Decimal("2000000"))

    @model_validator(mode="after")
    def _validate_combinations(self) -> "DonorInputs":
        # Hard block: gift-splitting requires a spouse (IRC §2513).
        if self.elect_gift_splitting and not self.spouse_present:
            raise ValueError(
                "Gift-splitting election requires a spouse (IRC §2513). "
                "Either set spouse_present=True or unset elect_gift_splitting."
            )
        # Hard block: MFJ/MFS filing status requires a spouse.
        if self.filing_status in (FilingStatus.MFJ, FilingStatus.MFS) and not self.spouse_present:
            raise ValueError(
                "Filing status MFJ/MFS requires spouse_present=True."
            )
        # NYC flag only valid for NY state.
        if self.nyc_resident and self.state != StateCode.NY:
            raise ValueError(
                "nyc_resident may only be True when state == NY."
            )
        # Planned retirement age, if supplied, must be after current age.
        if self.planned_retirement_age is not None and self.planned_retirement_age <= self.donor_age:
            raise ValueError(
                "planned_retirement_age must be later than donor_age."
            )
        return self

    model_config = {"json_encoders": {Decimal: lambda v: str(v)}}
