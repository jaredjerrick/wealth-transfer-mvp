"""TaxContext — the shared resolver for federal tax mechanics.

Every strategy module receives a `TaxContext` and a `StateRegime`. The context
owns the federal rules dict, exposes typed helpers (`gift_tax_on`, `estate_tax_on`,
`apply_kiddie_tax`, etc.), and tracks running state that crosses strategy
boundaries (lifetime gift exemption used, GST exemption used).

All math is `Decimal`. We never coerce to `float` for monetary computation —
the brittle rounding behavior would defeat the determinism requirement and
make pinned tests un-pinnable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP, getcontext
from pathlib import Path
from typing import Iterable, Optional

from .citations import Citation, CITATIONS
from .inputs import DonorInputs, FilingStatus

# 28 significant digits is enough to keep cents stable through 60-year projections.
getcontext().prec = 28

ZERO = Decimal("0")
CENT = Decimal("0.01")


def D(value) -> Decimal:
    """Coerce any number-ish input into a Decimal. Strings preferred over floats."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(value)


def round_cents(amount: Decimal) -> Decimal:
    """Round to two decimal places, HALF_UP (matches IRS rounding convention)."""
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Rules loader
# ---------------------------------------------------------------------------

DEFAULT_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "rules_2025.json"


def load_rules(path: Optional[Path] = None) -> dict:
    """Load and freeze the rules JSON for a given tax year."""
    target = Path(path) if path else DEFAULT_RULES_PATH
    with target.open() as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Bracket helpers
# ---------------------------------------------------------------------------

def progressive_tax(taxable: Decimal, brackets: list[dict]) -> Decimal:
    """Apply a progressive tax bracket schedule.

    Each bracket is `{"floor": ..., "ceiling": ... | None, "rate": ..., "base_tax": ...}`.
    `base_tax` is the cumulative tax owed at `floor`. This matches the structure
    of the IRC §2001(c) estate tax rate table and IRC §1 income brackets.
    """
    if taxable <= ZERO:
        return ZERO

    for b in brackets:
        floor = D(b["floor"])
        ceiling = D(b["ceiling"]) if b.get("ceiling") is not None else None
        if ceiling is None or taxable <= ceiling:
            base_tax = D(b["base_tax"])
            rate = D(b["rate"])
            return base_tax + (taxable - floor) * rate

    # Should never reach here for a well-formed schedule with an open top bracket.
    return ZERO


def flat_bracket_rate(taxable: Decimal, brackets: list[dict]) -> Decimal:
    """For preferential-rate schedules (cap gains), returns the marginal rate
    applicable to the entire amount. Used when computing tax on a single block
    of preferentially taxed income at the donor's overall income level."""
    if taxable <= ZERO:
        return ZERO
    for b in brackets:
        ceiling = D(b["ceiling"]) if b.get("ceiling") is not None else None
        if ceiling is None or taxable <= ceiling:
            return D(b["rate"])
    return D(brackets[-1]["rate"])


# ---------------------------------------------------------------------------
# Cross-strategy running state
# ---------------------------------------------------------------------------

@dataclass
class ExemptionLedger:
    """Tracks lifetime exemption usage across all strategies in a comparison.

    Each strategy is evaluated in isolation in the MVP — a fresh ledger is used
    per strategy. The struct exists so that future combined-strategy planning
    can flow through the same primitives without engine refactors.
    """

    gift_exemption_remaining: Decimal
    gst_exemption_remaining: Decimal

    @classmethod
    def fresh(cls, basic_exclusion: Decimal, gst_exemption: Decimal) -> "ExemptionLedger":
        return cls(basic_exclusion, gst_exemption)


# ---------------------------------------------------------------------------
# TaxContext
# ---------------------------------------------------------------------------

@dataclass
class TaxContext:
    """Federal-level tax resolver. State-specific math lives in `StateRegime`."""

    rules: dict
    inputs: DonorInputs

    # Convenience cached views
    federal: dict = field(init=False)
    defaults: dict = field(init=False)

    def __post_init__(self) -> None:
        self.federal = self.rules["federal"]
        self.defaults = self.rules["defaults"]

    # ----- accessors -----

    @property
    def tax_year(self) -> int:
        return self.rules["tax_year"]

    @property
    def annual_exclusion(self) -> Decimal:
        return D(self.federal["gift_tax"]["annual_exclusion_per_donee"]["value"])

    @property
    def basic_exclusion_amount(self) -> Decimal:
        return D(self.federal["estate_tax"]["basic_exclusion_amount"]["value"])

    @property
    def gst_exemption(self) -> Decimal:
        return D(self.federal["gst_tax"]["exemption"]["value"])

    @property
    def kiddie_tax_floor(self) -> Decimal:
        return D(self.federal["kiddie_tax_2025"]["unearned_income_at_parent_rate_floor"])

    @property
    def kiddie_tax_exempt(self) -> Decimal:
        return D(self.federal["kiddie_tax_2025"]["unearned_income_exempt"])

    @property
    def ira_limit(self) -> Decimal:
        return D(self.federal["retirement_accounts_2025"]["ira_contribution_limit"]["value"])

    @property
    def filing_status_key(self) -> str:
        return self.inputs.filing_status.value  # "single" | "mfj" | "mfs" | "hoh"

    # ----- federal income tax -----

    def federal_ordinary_tax(self, taxable: Decimal) -> Decimal:
        brackets = self.federal["income_tax_2025_ordinary"][self.filing_status_key]
        return progressive_tax(taxable, brackets)

    def federal_ordinary_marginal_rate(self, agi: Decimal) -> Decimal:
        brackets = self.federal["income_tax_2025_ordinary"][self.filing_status_key]
        return flat_bracket_rate(agi, brackets)

    def federal_ltcg_rate(self, agi: Decimal) -> Decimal:
        brackets = self.federal["capital_gains_2025_long_term"][self.filing_status_key]
        return flat_bracket_rate(agi, brackets)

    def niit_rate_applies(self, agi: Decimal) -> Decimal:
        niit = self.federal["niit"]
        threshold = D(niit["thresholds"][self.filing_status_key])
        return D(niit["rate"]) if agi > threshold else ZERO

    # ----- gift tax -----

    def annual_exclusion_total(self, num_donees: int = 1) -> Decimal:
        """Effective annual exclusion, accounting for spousal gift-splitting."""
        per = self.annual_exclusion
        if self.inputs.elect_gift_splitting and self.inputs.spouse_present:
            per = per * Decimal("2")
        return per * Decimal(num_donees)

    def gift_tax_on_taxable_gift(
        self,
        taxable_gift: Decimal,
        ledger: ExemptionLedger,
    ) -> tuple[Decimal, list[Citation]]:
        """Compute current-year gift tax (almost always zero until lifetime
        exemption is exhausted). Side effect: decrement `ledger.gift_exemption_remaining`.

        Returns (tax_due, citations).
        """
        cites = [CITATIONS["annual_exclusion"], CITATIONS["lifetime_exemption"]]
        if taxable_gift <= ZERO:
            return ZERO, cites

        # Consume lifetime exemption first.
        consumed = min(taxable_gift, ledger.gift_exemption_remaining)
        ledger.gift_exemption_remaining -= consumed
        excess = taxable_gift - consumed
        if excess <= ZERO:
            return ZERO, cites

        # Anything in excess of remaining exemption is taxed at the §2001(c) schedule.
        tax = progressive_tax(excess, self.federal["estate_tax"]["rate_schedule"]["brackets"])
        cites.append(CITATIONS["estate_rate_schedule"])
        return tax, cites

    # ----- estate tax (federal) -----

    def federal_estate_tax(
        self,
        taxable_estate: Decimal,
        applicable_exclusion: Optional[Decimal] = None,
    ) -> tuple[Decimal, list[Citation]]:
        """Federal estate tax on a taxable estate, after applying the unified credit.

        Args:
            taxable_estate: Gross estate minus §2053/§2056/§2055 deductions.
            applicable_exclusion: If None, uses §2010(c) basic exclusion. Pass a
                larger amount to model DSUE portability under §2010(c)(2)(B).

        Returns:
            (tax_due, citations).
        """
        cites = [CITATIONS["estate_rate_schedule"], CITATIONS["lifetime_exemption"]]
        if taxable_estate <= ZERO:
            return ZERO, cites

        exclusion = applicable_exclusion if applicable_exclusion is not None else self.basic_exclusion_amount

        # Compute tentative tax on the taxable estate, subtract unified credit
        # (the tentative tax that would have applied to the exclusion amount).
        brackets = self.federal["estate_tax"]["rate_schedule"]["brackets"]
        tentative_on_estate = progressive_tax(taxable_estate, brackets)
        unified_credit = progressive_tax(exclusion, brackets)
        net = tentative_on_estate - unified_credit
        return (net if net > ZERO else ZERO), cites

    # ----- kiddie tax -----

    def apply_kiddie_tax(
        self,
        child_unearned_income: Decimal,
        child_age: int,
        child_is_full_time_student: bool = False,
    ) -> tuple[Decimal, list[Citation]]:
        """IRC §1(g) kiddie tax. Returns (tax_due, citations).

        Applies if child is under 19, or under 24 and a full-time student.
        - First $1,350 (2025) is exempt (standard deduction for unearned).
        - Next $1,350 taxed at child's rate (treated as 10% for simplicity at this scale).
        - Unearned income > $2,700 taxed at parent's marginal rate.
        """
        cites = [CITATIONS["kiddie_tax"]]
        if child_unearned_income <= ZERO:
            return ZERO, cites

        applies = child_age < 19 or (child_age < 24 and child_is_full_time_student)
        if not applies:
            # Child filing as adult — taxed at single bracket.
            # We approximate with the child having no other income.
            single_brackets = self.federal["income_tax_2025_ordinary"]["single"]
            return progressive_tax(child_unearned_income, single_brackets), cites

        exempt = self.kiddie_tax_exempt
        kid_rate_band = self.kiddie_tax_floor - exempt  # $1,350
        child_rate = D("0.10")  # lowest ordinary bracket

        tax = ZERO
        remaining = child_unearned_income
        # Tier 1: exempt
        consumed = min(remaining, exempt)
        remaining -= consumed
        if remaining <= ZERO:
            return ZERO, cites
        # Tier 2: child's rate
        consumed = min(remaining, kid_rate_band)
        tax += consumed * child_rate
        remaining -= consumed
        if remaining <= ZERO:
            return round_cents(tax), cites
        # Tier 3: parent's marginal rate
        parent_marginal = self.federal_ordinary_marginal_rate(self.inputs.donor_gross_income_agi)
        tax += remaining * parent_marginal
        return round_cents(tax), cites

    # ----- GST (generation-skipping transfer) tax -----

    @property
    def gst_top_rate(self) -> Decimal:
        """GST tax rate is the maximum federal estate-tax rate (§2641)."""
        brackets = self.federal["estate_tax"]["rate_schedule"]["brackets"]
        return max((D(b["rate"]) for b in brackets), default=D("0.40"))

    def apply_gst(
        self,
        taxable_transfer: Decimal,
        gst_exemption_remaining: Optional[Decimal] = None,
    ) -> tuple[Decimal, Decimal, list[Citation]]:
        """Compute GST tax on a transfer to a skip person.

        Allocates remaining GST exemption (§2631) first; any excess is taxed at
        the §2641 maximum rate. Returns (gst_tax_due, exemption_remaining_after,
        citations).
        """
        cites = [CITATIONS["gst_exemption"], CITATIONS["skip_person"], CITATIONS["gst_rate"]]
        if taxable_transfer <= ZERO:
            remaining = gst_exemption_remaining if gst_exemption_remaining is not None else self.gst_exemption
            return ZERO, remaining, cites

        remaining = gst_exemption_remaining if gst_exemption_remaining is not None else self.gst_exemption
        sheltered = min(taxable_transfer, remaining)
        remaining -= sheltered
        excess = taxable_transfer - sheltered
        if excess <= ZERO:
            return ZERO, remaining, cites
        return round_cents(excess * self.gst_top_rate), remaining, cites

    # ----- portability / marital -----

    def applicable_exclusion_with_portability(self) -> Decimal:
        """If a spouse is present and donor elects portability via DSUE, the
        surviving spouse's applicable exclusion can be up to 2× basic exclusion.

        In MVP we model a simple deterministic case: if both spouses die within
        the horizon and the first spouse's exemption was unused, the survivor
        gets the full DSUE.
        """
        if self.inputs.spouse_present:
            return self.basic_exclusion_amount * Decimal("2")
        return self.basic_exclusion_amount


__all__ = [
    "TaxContext",
    "ExemptionLedger",
    "load_rules",
    "progressive_tax",
    "flat_bracket_rate",
    "D",
    "ZERO",
    "round_cents",
]
