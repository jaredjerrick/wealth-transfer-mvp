"""Shared pytest fixtures."""

from __future__ import annotations

from decimal import Decimal

import pytest

from engine.inputs import DonorInputs, FilingStatus, StateCode
from engine.tax_context import load_rules


@pytest.fixture(scope="session")
def rules() -> dict:
    return load_rules()


def _make_inputs(
    state: StateCode,
    net_worth: Decimal,
    *,
    donor_age: int = 50,
    donor_agi: Decimal = Decimal("250000"),
    filing_status: FilingStatus = FilingStatus.MFJ,
    spouse_present: bool = True,
    child_age: int = 5,
    child_earned_income: Decimal = Decimal("0"),
    annual_contribution: Decimal = Decimal("19000"),
    horizon: int = 18,
    expected_return: Decimal = Decimal("0.07"),
) -> DonorInputs:
    return DonorInputs(
        donor_age=donor_age,
        donor_gross_income_agi=donor_agi,
        filing_status=filing_status,
        state=state,
        donor_net_worth=net_worth,
        spouse_present=spouse_present,
        child_age=child_age,
        child_earned_income=child_earned_income,
        investment_horizon_years=horizon,
        annual_contribution=annual_contribution,
        expected_pretax_return=expected_return,
    )


@pytest.fixture
def low_net_worth_inputs():
    """$500K — well under any exemption."""
    def _build(state: StateCode = StateCode.IL) -> DonorInputs:
        return _make_inputs(state, Decimal("500000"))
    return _build


@pytest.fixture
def mid_net_worth_inputs():
    """$5M — over IL $4M but under NY $7.16M, under federal $13.99M."""
    def _build(state: StateCode = StateCode.IL) -> DonorInputs:
        return _make_inputs(state, Decimal("5000000"))
    return _build


@pytest.fixture
def high_net_worth_inputs():
    """$25M — over federal $13.99M and over NY's cliff."""
    def _build(state: StateCode = StateCode.IL) -> DonorInputs:
        return _make_inputs(state, Decimal("25000000"))
    return _build
