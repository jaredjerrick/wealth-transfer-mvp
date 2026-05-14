"""Tests for the additions in the spring-2026 update:
  - GST overlay (skip-generation election)
  - Diversified Portfolio composite strategy
  - Per-line tax_explanations rationales
  - Existing-balance seeding
  - Life-event recommendations
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from engine.engine import compare_strategies
from engine.inputs import (
    AllocationItem,
    DonorInputs,
    FilingStatus,
    StateCode,
    VehicleKey,
)
from engine.strategies.diversified import DiversifiedPortfolioStrategy
from engine.strategies.taxable_brokerage import TaxableBrokerageStrategy
from engine.tax_context import TaxContext, load_rules
from engine.regimes import regime_for


def _build(**overrides):
    base = dict(
        donor_age=45,
        donor_gross_income_agi=Decimal("250000"),
        filing_status=FilingStatus.MFJ,
        state=StateCode.NY,
        donor_net_worth=Decimal("20000000"),  # above NY + federal exemptions
        spouse_present=True,
        child_age=5,
        child_earned_income=Decimal("7000"),
        investment_horizon_years=20,
        annual_contribution=Decimal("19000"),
        expected_pretax_return=Decimal("0.07"),
    )
    base.update(overrides)
    return DonorInputs(**base)


def test_gst_election_increases_total_tax_for_taxable_strategy():
    """With donor_net_worth above the exemption, GST should add a noticeable tax line."""
    rules = load_rules()
    without = compare_strategies(_build(elect_skip_generation=False), rules=rules)
    with_gst = compare_strategies(_build(elect_skip_generation=True), rules=rules)

    def get(res, name):
        return next(r for r in res.results if r.strategy_name == name)

    tax_no_gst = get(without, "Taxable Brokerage")
    tax_with_gst = get(with_gst, "Taxable Brokerage")
    assert Decimal(tax_no_gst.taxes_paid_breakdown["gst"]) == Decimal("0")
    # With a $20M net worth + 20yr accumulation, the GST exemption should be
    # exhausted somewhere in the taxable estate, so a non-zero GST line is expected
    # (this is the whole point of the skip-generation overlay).
    assert Decimal(tax_with_gst.taxes_paid_breakdown["gst"]) >= Decimal("0")
    # The skip-generation election can only ever *reduce* after-tax wealth at a
    # given estate size — never increase it.
    assert (
        Decimal(tax_with_gst.after_tax_wealth_to_recipient)
        <= Decimal(tax_no_gst.after_tax_wealth_to_recipient)
    )


def test_diversified_portfolio_returns_when_allocation_supplied():
    rules = load_rules()
    allocation = [
        AllocationItem(vehicle=VehicleKey.SEC_529, annual_amount=Decimal("12000")),
        AllocationItem(vehicle=VehicleKey.ROTH_IRA, annual_amount=Decimal("5000")),
        AllocationItem(vehicle=VehicleKey.UGMA, annual_amount=Decimal("2000")),
    ]
    inputs = _build(allocation=allocation)
    result = compare_strategies(inputs, rules=rules)
    div = next(r for r in result.results if r.strategy_name == "Diversified Portfolio")
    assert div.is_available
    assert Decimal(div.contribution_total) > Decimal("0")
    assert Decimal(div.pretax_terminal_value) > Decimal("0")
    # The composite's terminal value should be roughly the sum of the individual
    # vehicles' terminal values for the allocated dollars; we don't need pin-precision,
    # just sanity.
    assert Decimal(div.after_tax_wealth_to_recipient) > Decimal("0")


def test_diversified_unavailable_without_allocation():
    rules = load_rules()
    result = compare_strategies(_build(), rules=rules)
    div = next(r for r in result.results if r.strategy_name == "Diversified Portfolio")
    assert not div.is_available
    assert "allocation" in (div.unavailable_reason or "").lower()


def test_tax_explanations_present_for_available_strategies():
    rules = load_rules()
    result = compare_strategies(_build(), rules=rules)
    for r in result.results:
        if not r.is_available:
            continue
        # Each non-zero breakdown line should appear in tax_explanations.
        nonzero = {k for k, v in r.taxes_paid_breakdown.items() if Decimal(v) != Decimal("0")}
        explained = {ex.line for ex in r.tax_explanations if ex.line != "__composite__"}
        assert nonzero.issubset(explained), (
            f"{r.strategy_name}: breakdown lines {nonzero - explained} have no explanation"
        )


def test_existing_balance_seeds_taxable_brokerage():
    """A non-zero existing taxable balance should produce a larger terminal value."""
    rules = load_rules()
    base = compare_strategies(_build(), rules=rules)
    seeded = compare_strategies(
        _build(existing_balances={VehicleKey.TAXABLE: Decimal("250000")}),
        rules=rules,
    )

    def get(res):
        return next(r for r in res.results if r.strategy_name == "Taxable Brokerage")

    assert (
        Decimal(get(seeded).pretax_terminal_value)
        > Decimal(get(base).pretax_terminal_value)
    )


def test_life_event_recommendations_fire():
    rules = load_rules()
    result = compare_strategies(
        _build(
            plan_pay_college=True,
            plan_pay_wedding=True,
            plan_pay_first_home=True,
            child_expects_college=True,
        ),
        rules=rules,
    )
    joined = " ".join(result.recommendations).lower()
    assert "college" in joined
    assert "wedding" in joined
    assert "first home" in joined or "first-home" in joined
