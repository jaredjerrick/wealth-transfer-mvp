"""Sanity tests for the remaining five strategies.

Per spec acceptance criteria: each strategy returns numerically defensible
results across $500K / $5M / $25M tiers in NY / IL / TX.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from engine.engine import compare_strategies
from engine.inputs import DonorInputs, FilingStatus, StateCode
from engine.strategies import (
    HoldUntilDeathStrategy,
    Section529Strategy,
    UGMAUTMAStrategy,
    TraditionalIRAStrategy,
    RothIRAStrategy,
)
from engine.regimes import regime_for
from engine.tax_context import TaxContext, ZERO


def _build(
    state: StateCode,
    net_worth: Decimal,
    *,
    horizon: int = 18,
    child_earned: Decimal = Decimal("0"),
    annual_contrib: Decimal = Decimal("19000"),
    five_yr: bool = False,
) -> DonorInputs:
    return DonorInputs(
        donor_age=45,
        donor_gross_income_agi=Decimal("250000"),
        filing_status=FilingStatus.MFJ,
        state=state,
        donor_net_worth=net_worth,
        spouse_present=True,
        child_age=0,
        child_earned_income=child_earned,
        investment_horizon_years=horizon,
        annual_contribution=annual_contrib,
        expected_pretax_return=Decimal("0.07"),
        elect_529_five_year=five_yr,
    )


# ---------------------------------------------------------------------------
# Hold-Until-Death
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state", [StateCode.NY, StateCode.IL, StateCode.TX])
def test_hold_until_death_runs(rules, state):
    inputs = _build(state, Decimal("500000"))
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(state, rules)
    res = HoldUntilDeathStrategy().evaluate(ctx, regime, inputs)
    assert res.is_available
    assert res.contribution_total == Decimal("342000.00")
    assert res.pretax_terminal_value > res.contribution_total
    # No estate tax at $500K + portfolio in any state with married couple.
    assert res.taxes_paid_breakdown["estate"] == Decimal("0")


def test_hold_until_death_beats_taxable_brokerage_at_low_levels(rules):
    """Hold-until-death has lower tax drag during accumulation (buy-and-hold),
    so terminal pretax value > Taxable Brokerage with active turnover."""
    from engine.strategies.taxable_brokerage import TaxableBrokerageStrategy
    inputs = _build(StateCode.IL, Decimal("500000"))
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(StateCode.IL, rules)
    hold = HoldUntilDeathStrategy().evaluate(ctx, regime, inputs)
    brokerage = TaxableBrokerageStrategy().evaluate(ctx, regime, inputs)
    assert hold.pretax_terminal_value > brokerage.pretax_terminal_value


def test_hold_until_death_ny_cliff_triggers_at_25m(rules):
    """$25M donor in NY → cliff warning surfaces."""
    inputs = _build(StateCode.NY, Decimal("25000000"))
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(StateCode.NY, rules)
    res = HoldUntilDeathStrategy().evaluate(ctx, regime, inputs)
    assert any("cliff" in w.lower() for w in res.warnings)


# ---------------------------------------------------------------------------
# 529
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state", [StateCode.NY, StateCode.IL, StateCode.TX])
def test_529_runs(rules, state):
    inputs = _build(state, Decimal("500000"))
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(state, rules)
    res = Section529Strategy().evaluate(ctx, regime, inputs)
    assert res.is_available
    # Tax-free growth — after-tax to recipient equals pretax terminal.
    assert res.after_tax_wealth_to_recipient == res.pretax_terminal_value


def test_529_il_provides_better_state_benefit_than_ny(rules):
    """IL allows $20K MFJ deduction vs. NY $10K → IL state benefit must be larger."""
    inputs_ny = _build(StateCode.NY, Decimal("500000"), annual_contrib=Decimal("20000"))
    inputs_il = _build(StateCode.IL, Decimal("500000"), annual_contrib=Decimal("20000"))

    ny = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs_ny),
        regime_for(StateCode.NY, rules),
        inputs_ny,
    )
    il = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs_il),
        regime_for(StateCode.IL, rules),
        inputs_il,
    )
    # Negative number = benefit. IL benefit (more negative) > NY.
    assert il.taxes_paid_breakdown["state_income"] < ny.taxes_paid_breakdown["state_income"]


def test_529_five_year_election_surfaces_citation(rules):
    """5-year election adds §529(c)(2)(B) to the citations bundle."""
    inputs = _build(StateCode.IL, Decimal("500000"), annual_contrib=Decimal("95000"), five_yr=True)
    res = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    sections = {c.section for c in res.citations}
    assert "IRC §529(c)(2)(B)" in sections


def test_529_tx_has_zero_state_benefit(rules):
    """Texas has no state income tax → no 529 deduction value."""
    inputs = _build(StateCode.TX, Decimal("500000"))
    res = Section529Strategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.TX, rules),
        inputs,
    )
    assert res.taxes_paid_breakdown["state_income"] == Decimal("0")


# ---------------------------------------------------------------------------
# UGMA/UTMA
# ---------------------------------------------------------------------------

def test_ugma_runs(rules):
    inputs = _build(StateCode.IL, Decimal("500000"))
    res = UGMAUTMAStrategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    assert res.is_available
    assert res.pretax_terminal_value > Decimal("0")


def test_ugma_kiddie_tax_warning(rules):
    """At meaningful contributions, kiddie tax should trigger and warn."""
    inputs = _build(StateCode.IL, Decimal("500000"), annual_contrib=Decimal("19000"))
    res = UGMAUTMAStrategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    assert any("kiddie" in w.lower() for w in res.warnings) or any(
        "majority" in w.lower() for w in res.warnings
    )


# ---------------------------------------------------------------------------
# Traditional IRA
# ---------------------------------------------------------------------------

def test_traditional_ira_blocked_without_earned_income(rules):
    inputs = _build(StateCode.IL, Decimal("500000"), child_earned=Decimal("0"))
    res = TraditionalIRAStrategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    assert not res.is_available
    assert "§219(b)" in res.unavailable_reason


def test_traditional_ira_with_earned_income(rules):
    inputs = _build(StateCode.IL, Decimal("500000"), child_earned=Decimal("7000"), annual_contrib=Decimal("7000"))
    res = TraditionalIRAStrategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    assert res.is_available
    # After-tax must be less than pretax terminal — ordinary income on distribution.
    assert res.after_tax_wealth_to_recipient < res.pretax_terminal_value


# ---------------------------------------------------------------------------
# Roth IRA
# ---------------------------------------------------------------------------

def test_roth_ira_blocked_without_earned_income(rules):
    inputs = _build(StateCode.IL, Decimal("500000"), child_earned=Decimal("0"))
    res = RothIRAStrategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    assert not res.is_available
    assert "§219(b)" in res.unavailable_reason or "§408A" in res.unavailable_reason


def test_roth_ira_full_tax_free(rules):
    """Roth: contributions capped at $7K/yr, after-tax = pretax terminal."""
    inputs = _build(StateCode.IL, Decimal("500000"), child_earned=Decimal("7000"), annual_contrib=Decimal("7000"))
    res = RothIRAStrategy().evaluate(
        TaxContext(rules=rules, inputs=inputs),
        regime_for(StateCode.IL, rules),
        inputs,
    )
    assert res.is_available
    assert res.after_tax_wealth_to_recipient == res.pretax_terminal_value
    assert res.taxes_paid_breakdown["income"] == Decimal("0")


def test_roth_beats_traditional_at_same_inputs(rules):
    """Tax-free corpus beats tax-deferred corpus at any positive marginal rate."""
    inputs = _build(
        StateCode.IL, Decimal("500000"),
        child_earned=Decimal("7000"),
        annual_contrib=Decimal("7000"),
        horizon=25,
    )
    ctx = TaxContext(rules=rules, inputs=inputs)
    regime = regime_for(StateCode.IL, rules)
    roth = RothIRAStrategy().evaluate(ctx, regime, inputs)
    trad = TraditionalIRAStrategy().evaluate(ctx, regime, inputs)
    assert roth.after_tax_wealth_to_recipient > trad.after_tax_wealth_to_recipient


# ---------------------------------------------------------------------------
# End-to-end compare
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("state", [StateCode.NY, StateCode.IL, StateCode.TX])
@pytest.mark.parametrize("net_worth", [Decimal("500000"), Decimal("5000000"), Decimal("25000000")])
def test_compare_runs_all_tiers_all_states(rules, state, net_worth):
    """Spec acceptance: every strategy returns a result for every state × tier combination."""
    inputs = _build(state, net_worth, child_earned=Decimal("7000"), horizon=15)
    result = compare_strategies(inputs, rules=rules)
    assert len(result.results) == 7
    # All strategies should be available because we provided earned income.
    available_count = sum(1 for r in result.results if r.is_available)
    assert available_count == 7, (
        f"Expected 7 available strategies for {state.value} @ ${net_worth}; "
        f"got {available_count}. Unavailable: "
        f"{[r.strategy_name for r in result.results if not r.is_available]}"
    )
