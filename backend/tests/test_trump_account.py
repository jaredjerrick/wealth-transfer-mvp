"""Trump Account strategy (OBBBA §70404) — pinned scenarios."""

from __future__ import annotations

from decimal import Decimal

import pytest

from engine.inputs import DonorInputs, FilingStatus, StateCode
from engine.strategies.trump_account import TrumpAccountStrategy
from engine.regimes import regime_for
from engine.tax_context import TaxContext


def _build(
    state: StateCode,
    *,
    child_age: int = 0,
    horizon: int = 18,
    annual_contrib: Decimal = Decimal("5000"),
    net_worth: Decimal = Decimal("500000"),
) -> DonorInputs:
    return DonorInputs(
        donor_age=35,
        donor_gross_income_agi=Decimal("150000"),
        filing_status=FilingStatus.MFJ,
        state=state,
        donor_net_worth=net_worth,
        spouse_present=True,
        child_age=child_age,
        investment_horizon_years=horizon,
        annual_contribution=annual_contrib,
        expected_pretax_return=Decimal("0.07"),
    )


def test_newborn_in_2025_gets_federal_seed(rules):
    """Child age 0 in tax_year 2025 → birth year 2025 → seed applied.

    FV of $5K/yr for 18 yrs at 7% (begin-of-year) = $181,895.
    $1,000 seed × 1.07^18 ≈ $3,380 → total ≈ $185,275.
    """
    inputs = _build(StateCode.IL, child_age=0, horizon=18)
    ctx = TaxContext(rules=rules, inputs=inputs)
    res = TrumpAccountStrategy().evaluate(ctx, regime_for(StateCode.IL, rules), inputs)
    assert res.is_available
    # The seed contribution to terminal value: $1,000 × 1.07^18 ≈ $3,380.
    # Without the seed we'd see ≈ $181,895. With the seed ≈ $185,275.
    assert Decimal("184000") < res.pretax_terminal_value < Decimal("187000"), \
        f"Pretax terminal {res.pretax_terminal_value} should be ~$185,275 (seed + 18 × $5K @ 7%)"
    # Citations must include the seed and the act.
    sections = {c.section for c in res.citations}
    assert "OBBBA §70404 (Pub. L. 119-21)" in sections
    assert "OBBBA §70404(b)" in sections


def test_older_child_not_in_seed_window(rules):
    """Child age 10 in 2025 → born 2015 → outside seed window. Warning surfaces."""
    inputs = _build(StateCode.IL, child_age=10, horizon=8)
    ctx = TaxContext(rules=rules, inputs=inputs)
    res = TrumpAccountStrategy().evaluate(ctx, regime_for(StateCode.IL, rules), inputs)
    assert res.is_available
    assert any("seed NOT applied" in w for w in res.warnings)
    # Seed citation should NOT be in the list since not eligible.
    sections = {c.section for c in res.citations}
    assert "OBBBA §70404(b)" not in sections


def test_contribution_capped_at_5000(rules):
    """User inputs $19K/yr — Trump Account caps it at $5K."""
    inputs = _build(StateCode.IL, child_age=0, horizon=18, annual_contrib=Decimal("19000"))
    ctx = TaxContext(rules=rules, inputs=inputs)
    res = TrumpAccountStrategy().evaluate(ctx, regime_for(StateCode.IL, rules), inputs)
    # Contribution total = 18 × $5K cap = $90K.
    assert res.contribution_total == Decimal("90000.00")
    assert any("exceeds the §70404(c)(1) parent cap" in w for w in res.warnings)


def test_short_horizon_below_age_18_warning(rules):
    """Child currently 5, horizon 10 years → terminal age 15, below access age 18."""
    inputs = _build(StateCode.IL, child_age=5, horizon=10)
    ctx = TaxContext(rules=rules, inputs=inputs)
    res = TrumpAccountStrategy().evaluate(ctx, regime_for(StateCode.IL, rules), inputs)
    assert any("below the §70404(f) access age" in w for w in res.warnings)


def test_tx_has_no_state_distribution_tax(rules):
    """Texas: no state income tax on distribution at age 18."""
    inputs = _build(StateCode.TX, child_age=0, horizon=18)
    ctx = TaxContext(rules=rules, inputs=inputs)
    res = TrumpAccountStrategy().evaluate(ctx, regime_for(StateCode.TX, rules), inputs)
    assert res.taxes_paid_breakdown["state_income"] == Decimal("0.00")


def test_trump_account_is_not_in_donors_estate(rules):
    """No estate tax line because corpus is the child's, not the donor's."""
    inputs = _build(StateCode.NY, child_age=0, horizon=18, net_worth=Decimal("50000000"))
    ctx = TaxContext(rules=rules, inputs=inputs)
    res = TrumpAccountStrategy().evaluate(ctx, regime_for(StateCode.NY, rules), inputs)
    assert res.taxes_paid_breakdown["estate"] == Decimal("0.00")
    assert res.taxes_paid_breakdown["state_estate"] == Decimal("0.00")


def test_trump_seed_beats_no_seed_at_same_inputs(rules):
    """Sanity: a newborn-eligible child accumulates more than an older child given
    identical horizon-length contribution streams (seed is the only difference)."""
    eligible = _build(StateCode.IL, child_age=0, horizon=18)
    ineligible = _build(StateCode.IL, child_age=10, horizon=18)
    r_eligible = TrumpAccountStrategy().evaluate(
        TaxContext(rules=rules, inputs=eligible),
        regime_for(StateCode.IL, rules),
        eligible,
    )
    r_ineligible = TrumpAccountStrategy().evaluate(
        TaxContext(rules=rules, inputs=ineligible),
        regime_for(StateCode.IL, rules),
        ineligible,
    )
    assert r_eligible.pretax_terminal_value > r_ineligible.pretax_terminal_value
