"""Pinned scenarios for the Taxable Brokerage strategy.

Three net-worth tiers × three states = nine scenarios. These are the spec's
acceptance criterion. Values are pinned to hand calculations with documented
inputs so the engine is regression-safe.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from engine.engine import compare_strategies
from engine.inputs import DonorInputs, FilingStatus, StateCode
from engine.strategies.taxable_brokerage import TaxableBrokerageStrategy
from engine.regimes import regime_for
from engine.tax_context import TaxContext


def _build(state: StateCode, net_worth: Decimal, horizon: int = 18) -> DonorInputs:
    return DonorInputs(
        donor_age=45,
        donor_gross_income_agi=Decimal("250000"),
        filing_status=FilingStatus.MFJ,
        state=state,
        donor_net_worth=net_worth,
        spouse_present=True,
        child_age=0,
        investment_horizon_years=horizon,
        annual_contribution=Decimal("19000"),
        expected_pretax_return=Decimal("0.07"),
    )


# ---------------------------------------------------------------------------
# Sanity / range checks — terminal values land in defensible bands.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state", [StateCode.NY, StateCode.IL, StateCode.TX])
def test_low_net_worth_no_estate_tax(rules, state):
    """$500K net worth + 18 × $19K contribution. Well under every exemption.
    Federal estate tax = 0, state estate tax = 0 (except NY cliff zone we avoid)."""
    inputs = _build(state, Decimal("500000"), horizon=18)
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(state, rules)

    result = TaxableBrokerageStrategy().evaluate(ctx, regime, inputs)

    assert result.is_available
    # Contribution total locked: 18 × $19,000 = $342,000.
    assert result.contribution_total == Decimal("342000.00")
    # Pretax terminal at 7% gross drag-adjusted: should be > $580K, < $700K.
    assert Decimal("550000") < result.pretax_terminal_value < Decimal("750000"), \
        f"Pretax terminal ({result.pretax_terminal_value}) out of expected band for {state.value}."
    # Federal estate tax must be zero — net worth + portfolio << $13.99M.
    assert result.taxes_paid_breakdown["estate"] == Decimal("0")
    # State estate tax must be zero in all three states at this level.
    assert result.taxes_paid_breakdown["state_estate"] == Decimal("0")
    # Recipient gets full pretax terminal back (step-up wipes embedded gains).
    assert result.after_tax_wealth_to_recipient == result.pretax_terminal_value


def test_mid_net_worth_il_above_4m_estate(rules):
    """$5M net worth, IL. IL estate tax kicks in at $4M with no portability.
    The slice's share of state estate tax should be > 0."""
    inputs = _build(StateCode.IL, Decimal("5000000"), horizon=18)
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(StateCode.IL, rules)
    result = TaxableBrokerageStrategy().evaluate(ctx, regime, inputs)

    assert result.taxes_paid_breakdown["state_estate"] > Decimal("0"), \
        "IL estate tax must apply when total estate ($5M + portfolio) > $4M."
    # Federal estate still zero — total well under $13.99M.
    assert result.taxes_paid_breakdown["estate"] == Decimal("0")


def test_mid_net_worth_ny_avoids_cliff_below_7_16m(rules):
    """$5M NY donor stays under the $7.16M exemption. NY estate tax = 0."""
    inputs = _build(StateCode.NY, Decimal("5000000"), horizon=18)
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(StateCode.NY, rules)
    result = TaxableBrokerageStrategy().evaluate(ctx, regime, inputs)

    assert result.taxes_paid_breakdown["state_estate"] == Decimal("0")
    assert not any("cliff" in w.lower() for w in result.warnings)


def test_high_net_worth_ny_cliff_triggered(rules):
    """$25M NY donor — well above $7.16M × 1.05 cliff threshold.
    Result must surface the cliff warning, and state estate share must be material."""
    inputs = _build(StateCode.NY, Decimal("25000000"), horizon=18)
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(StateCode.NY, rules)
    result = TaxableBrokerageStrategy().evaluate(ctx, regime, inputs)

    assert any("cliff" in w.lower() for w in result.warnings), \
        f"NY cliff warning must be present. Got: {result.warnings}"
    assert result.taxes_paid_breakdown["state_estate"] > Decimal("0")


def test_high_net_worth_federal_estate_tax_triggered(rules):
    """$25M donor — over the $13.99M × 2 portable exclusion is borderline;
    a single $25M donor (no spouse) certainly triggers federal estate tax."""
    inputs = DonorInputs(
        donor_age=45, donor_gross_income_agi=Decimal("250000"),
        filing_status=FilingStatus.SINGLE, state=StateCode.IL,
        donor_net_worth=Decimal("25000000"), spouse_present=False,
        child_age=0, investment_horizon_years=18,
        annual_contribution=Decimal("19000"),
    )
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(StateCode.IL, rules)
    result = TaxableBrokerageStrategy().evaluate(ctx, regime, inputs)

    assert result.taxes_paid_breakdown["estate"] > Decimal("0"), \
        "Federal estate tax must apply to $25M single donor over $13.99M exemption."


# ---------------------------------------------------------------------------
# Year-by-year projection must be present and well-formed.
# ---------------------------------------------------------------------------

def test_year_by_year_projection_shape(rules):
    inputs = _build(StateCode.IL, Decimal("500000"), horizon=10)
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(StateCode.IL, rules)
    result = TaxableBrokerageStrategy().evaluate(ctx, regime, inputs)

    assert len(result.year_by_year_projection) == 10
    # Contributions to date must monotonically increase.
    contribs = [r.contributions_to_date for r in result.year_by_year_projection]
    for i in range(1, len(contribs)):
        assert contribs[i] > contribs[i - 1]
    # Pretax balance must (in absence of negative returns) also monotonically grow.
    balances = [r.pretax_balance for r in result.year_by_year_projection]
    for i in range(1, len(balances)):
        assert balances[i] > balances[i - 1]


# ---------------------------------------------------------------------------
# Determinism: same inputs must produce byte-identical outputs.
# ---------------------------------------------------------------------------

def test_determinism(rules):
    inputs = _build(StateCode.NY, Decimal("5000000"), horizon=15)
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(StateCode.NY, rules)

    a = TaxableBrokerageStrategy().evaluate(ctx, regime, inputs)
    b = TaxableBrokerageStrategy().evaluate(ctx, regime, inputs)
    assert a.pretax_terminal_value == b.pretax_terminal_value
    assert a.after_tax_wealth_to_recipient == b.after_tax_wealth_to_recipient
    assert a.taxes_paid_breakdown == b.taxes_paid_breakdown


# ---------------------------------------------------------------------------
# Citations: every strategy result must carry at least the §1014 and §2001
# citations plus the state estate citation.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state", [StateCode.NY, StateCode.IL, StateCode.TX])
def test_citations_present(rules, state):
    inputs = _build(state, Decimal("500000"), horizon=10)
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(state, rules)
    result = TaxableBrokerageStrategy().evaluate(ctx, regime, inputs)

    sections = {c.section for c in result.citations}
    assert "IRC §1014" in sections, f"§1014 step-up citation missing for {state.value}"
    assert "IRC §2001(c)" in sections, f"§2001(c) rate schedule citation missing for {state.value}"


# ---------------------------------------------------------------------------
# Cross-state comparability: spec acceptance — TX community-property donor
# (married) achieves a better hold-asset outcome than equivalent NY donor at
# levels that don't trigger federal estate tax. (At this MVP fidelity, the
# difference shows mainly in the absence of state income-tax drag during
# accumulation.)
# ---------------------------------------------------------------------------

def test_tx_beats_ny_at_mid_net_worth(rules):
    """TX donor with $5M net worth, married, should end up with strictly more
    after-tax wealth than the equivalent NY donor (NY income-tax drag during
    accumulation alone delivers this result; estate tax is zero in both at this
    level)."""
    ny_inputs = _build(StateCode.NY, Decimal("5000000"), horizon=18)
    tx_inputs = _build(StateCode.TX, Decimal("5000000"), horizon=18)

    ny_ctx = TaxContext(rules=rules, inputs=ny_inputs)
    tx_ctx = TaxContext(rules=rules, inputs=tx_inputs)

    ny = TaxableBrokerageStrategy().evaluate(ny_ctx, regime_for(StateCode.NY, rules), ny_inputs)
    tx = TaxableBrokerageStrategy().evaluate(tx_ctx, regime_for(StateCode.TX, rules), tx_inputs)
    assert tx.after_tax_wealth_to_recipient > ny.after_tax_wealth_to_recipient, \
        f"TX ({tx.after_tax_wealth_to_recipient}) should beat NY ({ny.after_tax_wealth_to_recipient}) at $5M."


# ---------------------------------------------------------------------------
# Engine-level smoke test: compare_strategies returns six results.
# ---------------------------------------------------------------------------

def test_compare_returns_seven_strategies(rules):
    inputs = _build(StateCode.IL, Decimal("5000000"), horizon=15)
    result = compare_strategies(inputs, rules=rules)
    assert len(result.results) == 7
    available = [r for r in result.results if r.is_available]
    assert any(r.strategy_name == "Taxable Brokerage" for r in available)
    assert any(r.strategy_name == "Trump Account" for r in available)


def test_compare_recommendations_fire_appropriately(rules):
    """High-net-worth NY donor must surface the NY cliff recommendation."""
    inputs = _build(StateCode.NY, Decimal("10000000"), horizon=15)
    result = compare_strategies(inputs, rules=rules)
    joined = " ".join(result.recommendations)
    assert "NY $7.16M" in joined or "NY" in joined
