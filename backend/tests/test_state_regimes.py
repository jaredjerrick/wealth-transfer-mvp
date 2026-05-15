"""State regime unit tests — NY cliff, IL graduated, TX no-tax."""

from __future__ import annotations

from decimal import Decimal

import pytest

from engine.inputs import DonorInputs, FilingStatus, StateCode
from engine.regimes import NYRegime, ILRegime, TXRegime


@pytest.fixture
def inputs_mfj_ny(rules):
    return DonorInputs(
        donor_age=60,
        donor_gross_income_agi=Decimal("250000"),
        filing_status=FilingStatus.MFJ,
        state=StateCode.NY,
        donor_net_worth=Decimal("8000000"),
        spouse_present=True,
        child_age=10,
        investment_horizon_years=10,
        annual_contribution=Decimal("19000"),
    )


# ----- NY -----

def test_ny_below_exemption_zero_tax(rules, inputs_mfj_ny):
    regime = NYRegime(rules)
    res = regime.state_estate_tax(
        gross_estate=Decimal("7000000"),
        marital_deduction=Decimal("0"),
        charitable_deduction=Decimal("0"),
        admin_debts_deduction=Decimal("0"),
        inputs=inputs_mfj_ny,
    )
    assert res.state_estate_tax == Decimal("0")
    assert not res.cliff_triggered


def test_ny_cliff_triggered_above_105_pct(rules, inputs_mfj_ny):
    """Above 1.05 × $7.35M = $7,717,500 (2026), entire estate taxed without exemption."""
    regime = NYRegime(rules)
    res = regime.state_estate_tax(
        gross_estate=Decimal("8000000"),
        marital_deduction=Decimal("0"),
        charitable_deduction=Decimal("0"),
        admin_debts_deduction=Decimal("0"),
        inputs=inputs_mfj_ny,
    )
    assert res.cliff_triggered, "NY cliff should be triggered at $8M (above $7.518M)"
    assert res.state_estate_tax > Decimal("0")
    # Discontinuity check: a $7.16M estate pays $0, an $8M estate pays much more
    # than 10% × $840K marginal — that's the cliff trap.
    assert res.state_estate_tax > Decimal("100000"), \
        f"Cliff tax of {res.state_estate_tax} should be >$100K to show discontinuity"
    assert any("cliff" in w.lower() for w in res.warnings)


def test_ny_cliff_discontinuity(rules, inputs_mfj_ny):
    """Compare an estate at the 2026 NY BEA ($7.35M) vs. above the cliff threshold."""
    regime = NYRegime(rules)
    at_exemption = regime.state_estate_tax(
        Decimal("7350000"), Decimal("0"), Decimal("0"), Decimal("0"), inputs_mfj_ny
    )
    way_over = regime.state_estate_tax(
        Decimal("8000000"), Decimal("0"), Decimal("0"), Decimal("0"), inputs_mfj_ny
    )
    # A $650K marginal addition produces a far-greater-than-$650K tax delta,
    # demonstrating the cliff is destructive of the exemption.
    delta_tax = way_over.state_estate_tax - at_exemption.state_estate_tax
    assert delta_tax > Decimal("400000"), \
        f"Cliff should produce massive marginal tax — got {delta_tax} on $650K of additional estate"


def test_ny_income_tax_at_250k_mfj(rules, inputs_mfj_ny):
    regime = NYRegime(rules)
    res = regime.state_income_tax(Decimal("250000"), inputs_mfj_ny)
    # NY MFJ at $250K sits in the 6% bracket ($161,550–$323,200).
    # base_tax at $161,550 = $8,552.75; over = $88,450 × 0.06 = $5,307.
    # Total ≈ $13,860.
    assert abs(res.state_income_tax - Decimal("13859.75")) < Decimal("2")


def test_ny_529_deduction_mfj_capped_at_10k(rules, inputs_mfj_ny):
    regime = NYRegime(rules)
    deductible, _ = regime.section_529_deduction(Decimal("25000"), inputs_mfj_ny)
    assert deductible == Decimal("10000")


# ----- IL -----

def test_il_flat_income_tax(rules):
    inputs = DonorInputs(
        donor_age=50, donor_gross_income_agi=Decimal("250000"),
        filing_status=FilingStatus.MFJ, state=StateCode.IL,
        donor_net_worth=Decimal("1000000"), spouse_present=True,
        child_age=5, investment_horizon_years=10,
        annual_contribution=Decimal("19000"),
    )
    regime = ILRegime(rules)
    res = regime.state_income_tax(Decimal("250000"), inputs)
    assert res.state_income_tax == Decimal("12375.00")  # 250000 × 0.0495


def test_il_below_4m_no_estate_tax(rules):
    inputs = DonorInputs(
        donor_age=50, donor_gross_income_agi=Decimal("250000"),
        filing_status=FilingStatus.MFJ, state=StateCode.IL,
        donor_net_worth=Decimal("3000000"), spouse_present=True,
        child_age=5, investment_horizon_years=10, annual_contribution=Decimal("19000"),
    )
    regime = ILRegime(rules)
    res = regime.state_estate_tax(
        Decimal("3500000"), Decimal("0"), Decimal("0"), Decimal("0"), inputs
    )
    assert res.state_estate_tax == Decimal("0")


def test_il_above_4m_taxed_on_excess(rules):
    inputs = DonorInputs(
        donor_age=50, donor_gross_income_agi=Decimal("250000"),
        filing_status=FilingStatus.MFJ, state=StateCode.IL,
        donor_net_worth=Decimal("5000000"), spouse_present=True,
        child_age=5, investment_horizon_years=10, annual_contribution=Decimal("19000"),
    )
    regime = ILRegime(rules)
    res = regime.state_estate_tax(
        Decimal("6000000"), Decimal("0"), Decimal("0"), Decimal("0"), inputs
    )
    assert res.state_estate_tax > Decimal("0")
    assert not res.cliff_triggered


def test_il_529_deduction_mfj_capped_at_20k(rules):
    inputs = DonorInputs(
        donor_age=50, donor_gross_income_agi=Decimal("250000"),
        filing_status=FilingStatus.MFJ, state=StateCode.IL,
        donor_net_worth=Decimal("1000000"), spouse_present=True,
        child_age=5, investment_horizon_years=10, annual_contribution=Decimal("19000"),
    )
    regime = ILRegime(rules)
    deductible, _ = regime.section_529_deduction(Decimal("25000"), inputs)
    assert deductible == Decimal("20000")


# ----- TX -----

def test_tx_zero_income_tax(rules):
    inputs = DonorInputs(
        donor_age=50, donor_gross_income_agi=Decimal("500000"),
        filing_status=FilingStatus.MFJ, state=StateCode.TX,
        donor_net_worth=Decimal("1000000"), spouse_present=True,
        child_age=5, investment_horizon_years=10, annual_contribution=Decimal("19000"),
    )
    regime = TXRegime(rules)
    assert regime.state_income_tax(Decimal("500000"), inputs).state_income_tax == Decimal("0")


def test_tx_zero_estate_tax(rules):
    inputs = DonorInputs(
        donor_age=50, donor_gross_income_agi=Decimal("250000"),
        filing_status=FilingStatus.MFJ, state=StateCode.TX,
        donor_net_worth=Decimal("50000000"), spouse_present=True,
        child_age=5, investment_horizon_years=10, annual_contribution=Decimal("19000"),
    )
    regime = TXRegime(rules)
    res = regime.state_estate_tax(
        Decimal("50000000"), Decimal("0"), Decimal("0"), Decimal("0"), inputs
    )
    assert res.state_estate_tax == Decimal("0")


def test_tx_is_community_property(rules):
    assert TXRegime(rules).is_community_property is True


def test_ny_il_not_community_property(rules):
    assert NYRegime(rules).is_community_property is False
    assert ILRegime(rules).is_community_property is False
