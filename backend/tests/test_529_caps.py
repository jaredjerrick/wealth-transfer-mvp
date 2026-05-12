"""Tests for the §529(b)(7) aggregate cap and age-22 contribution cutoff.

These scenarios were added in response to product feedback: the engine must
not let users 'contribute' to a 529 indefinitely. Two binding constraints:

  1. Aggregate per-beneficiary cap (state-specific): NY $520K, IL $500K, TX $500K
  2. Default age-22 cutoff (beneficiary's typical undergrad completion)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from engine.inputs import DonorInputs, FilingStatus, StateCode
from engine.regimes import regime_for
from engine.strategies.section_529 import Section529Strategy
from engine.tax_context import TaxContext


def _build(
    state: StateCode,
    *,
    child_age: int,
    horizon: int,
    annual: Decimal,
) -> DonorInputs:
    return DonorInputs(
        donor_age=45,
        donor_gross_income_agi=Decimal("250000"),
        filing_status=FilingStatus.MFJ,
        state=state,
        donor_net_worth=Decimal("1000000"),
        spouse_present=True,
        child_age=child_age,
        investment_horizon_years=horizon,
        annual_contribution=annual,
        expected_pretax_return=Decimal("0.07"),
    )


# ---------------------------------------------------------------------------
# Age-22 cutoff
# ---------------------------------------------------------------------------

def test_age_22_cutoff_binds(rules):
    """Child currently 18, horizon 10 years → only 5 years of contributions
    (ages 18, 19, 20, 21, 22) before the cutoff triggers at age 23."""
    inputs = _build(StateCode.IL, child_age=18, horizon=10, annual=Decimal("19000"))
    res = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    # 5 years × $19K = $95K of contributions.
    assert res.contribution_total == Decimal("95000.00"), \
        f"Expected 5 years × $19K = $95K. Got {res.contribution_total}"
    # Warning must mention the age cutoff.
    assert any("age-22 education-funding window" in w or "past the default age" in w
               for w in res.warnings), f"Age-cutoff warning missing. Got: {res.warnings}"


def test_no_age_cutoff_when_child_still_young(rules):
    """Child age 5, horizon 15 years → contributions every year (ends at age 20)."""
    inputs = _build(StateCode.IL, child_age=5, horizon=15, annual=Decimal("19000"))
    res = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    assert res.contribution_total == Decimal("285000.00")  # 15 × $19K
    # No age-cutoff warning should fire.
    assert not any("age-22" in w or "past the default age" in w for w in res.warnings)


def test_age_cutoff_with_long_horizon_stops_contributions(rules):
    """Child 5, horizon 40 — contributions stop at year 18 (child turns 23)."""
    inputs = _build(StateCode.IL, child_age=5, horizon=40, annual=Decimal("19000"))
    res = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    # 18 years of contributions (ages 5..22) × $19K = $342K
    assert res.contribution_total == Decimal("342000.00"), \
        f"Expected 18 years × $19K = $342K (contributions through age 22). Got {res.contribution_total}"
    # Corpus continues to grow tax-free for the remaining 22 years.
    # FV of $342K corpus growing at 7% for 22 years ≈ $1.51M+
    assert res.pretax_terminal_value > Decimal("1300000")


# ---------------------------------------------------------------------------
# Aggregate state cap
# ---------------------------------------------------------------------------

def test_aggregate_cap_hard_stop_il(rules):
    """IL cap is $500K. With $100K/yr contributions, the cap binds in year 5."""
    inputs = _build(StateCode.IL, child_age=0, horizon=10, annual=Decimal("100000"))
    res = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    # Year 0: $100K → cum $100K
    # Year 1: $100K → cum $200K
    # Year 2: $100K → cum $300K
    # Year 3: $100K → cum $400K
    # Year 4: $100K → cum $500K (cap reached this year)
    # Years 5+: cap binds, no more contributions
    assert res.contribution_total == Decimal("500000.00"), \
        f"Expected $500K aggregate cap to bind. Got {res.contribution_total}"
    assert any("aggregate cap" in w.lower() for w in res.warnings)


def test_aggregate_cap_partial_year_topup_ny(rules):
    """NY cap is $520K. With $120K/yr, year 5 partially binds:
    cumulative reaches $480K after year 3, then year 4 tops up to $520K
    with only $40K of the requested $120K."""
    inputs = _build(StateCode.NY, child_age=0, horizon=10, annual=Decimal("120000"))
    res = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.NY, rules),
        inputs,
    )
    assert res.contribution_total == Decimal("520000.00"), \
        f"Expected NY cap of $520K. Got {res.contribution_total}"
    assert any("partially binds" in w or "aggregate cap" in w.lower() for w in res.warnings)


def test_aggregate_cap_does_not_bind_at_low_contributions(rules):
    """$10K/yr × 18 yrs = $180K, well under any state cap."""
    inputs = _build(StateCode.IL, child_age=5, horizon=18, annual=Decimal("10000"))
    res = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    assert res.contribution_total == Decimal("180000.00")
    assert not any("aggregate cap" in w.lower() for w in res.warnings)


# ---------------------------------------------------------------------------
# Citations and assumptions
# ---------------------------------------------------------------------------

def test_safeguards_citation_present(rules):
    """Every 529 result must carry the §529(b)(7) safeguards citation."""
    inputs = _build(StateCode.IL, child_age=5, horizon=18, annual=Decimal("19000"))
    res = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    sections = {c.section for c in res.citations}
    assert "IRC §529(b)(7)" in sections


def test_assumptions_mention_caps(rules):
    """Assumptions panel must reference both the age cutoff and the aggregate cap."""
    inputs = _build(StateCode.NY, child_age=5, horizon=18, annual=Decimal("19000"))
    res = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.NY, rules),
        inputs,
    )
    joined = " ".join(res.assumptions)
    assert "age 22" in joined or "age-22" in joined or "age 22" in joined.replace("age 22", "age 22")
    assert "$520,000" in joined or "aggregate" in joined.lower()


# ---------------------------------------------------------------------------
# Determinism preserved with caps in play
# ---------------------------------------------------------------------------

def test_determinism_with_caps(rules):
    """Same inputs → byte-identical outputs even when caps bind."""
    inputs = _build(StateCode.NY, child_age=0, horizon=40, annual=Decimal("100000"))
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(StateCode.NY, rules)
    a = Section529Strategy().evaluate(ctx, regime, inputs)
    b = Section529Strategy().evaluate(ctx, regime, inputs)
    assert a.contribution_total == b.contribution_total
    assert a.pretax_terminal_value == b.pretax_terminal_value
    assert a.warnings == b.warnings
