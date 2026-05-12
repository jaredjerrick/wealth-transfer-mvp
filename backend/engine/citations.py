"""Citation primitive.

Every numeric output that ships from the engine carries a list of `Citation`
records tracing the calculation back to its controlling authority. The UI
renders these as superscript footnotes with hover detail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Citation:
    """A single legal authority reference.

    Attributes:
        section: The IRC section, Treasury reg, or state statute (e.g. "IRC §2503(b)").
        description: One-line summary of the rule.
        url: Optional URL to the authority on irs.gov / cornell.edu / state DOR.
        scope: One of {"federal", "state", "treasury_reg", "rev_proc", "case"}.
    """

    section: str
    description: str
    url: Optional[str] = None
    scope: str = "federal"

    def to_dict(self) -> dict:
        return {
            "section": self.section,
            "description": self.description,
            "url": self.url,
            "scope": self.scope,
        }


# Canonical citations referenced repeatedly across the engine.
# Defining them once here prevents string drift.
CITATIONS = {
    # ---- Gift tax ----
    "annual_exclusion": Citation(
        section="IRC §2503(b)",
        description="Annual gift tax exclusion ($19,000 per donee for 2025).",
        url="https://www.law.cornell.edu/uscode/text/26/2503",
    ),
    "gift_splitting": Citation(
        section="IRC §2513",
        description="Spousal gift-splitting election doubles the annual exclusion.",
        url="https://www.law.cornell.edu/uscode/text/26/2513",
    ),
    "five_year_election_529": Citation(
        section="IRC §529(c)(2)(B)",
        description="Five-year forward election for 529 contributions.",
        url="https://www.law.cornell.edu/uscode/text/26/529",
    ),
    "marital_deduction_gift": Citation(
        section="IRC §2523",
        description="Unlimited gift tax marital deduction for U.S.-citizen spouse.",
        url="https://www.law.cornell.edu/uscode/text/26/2523",
    ),
    "lifetime_exemption": Citation(
        section="IRC §2010(c)",
        description="Basic exclusion amount applicable to estate and gift tax ($13.99M, 2025).",
        url="https://www.law.cornell.edu/uscode/text/26/2010",
    ),
    "completed_gift": Citation(
        section="IRC §2511",
        description="Transfers in trust or otherwise are subject to gift tax.",
        url="https://www.law.cornell.edu/uscode/text/26/2511",
    ),
    # ---- Estate tax ----
    "estate_rate_schedule": Citation(
        section="IRC §2001(c)",
        description="Federal unified transfer tax rate schedule (top 40%).",
        url="https://www.law.cornell.edu/uscode/text/26/2001",
    ),
    "portability_dsue": Citation(
        section="IRC §2010(c)(2)(B), (c)(4)",
        description="Deceased spousal unused exclusion portability.",
        url="https://www.law.cornell.edu/uscode/text/26/2010",
    ),
    "marital_deduction_estate": Citation(
        section="IRC §2056",
        description="Unlimited estate tax marital deduction for U.S.-citizen surviving spouse.",
        url="https://www.law.cornell.edu/uscode/text/26/2056",
    ),
    "charitable_deduction_estate": Citation(
        section="IRC §2055",
        description="Unlimited estate tax charitable deduction.",
        url="https://www.law.cornell.edu/uscode/text/26/2055",
    ),
    "admin_debts_deduction": Citation(
        section="IRC §2053",
        description="Deduction for administration expenses and decedent's debts.",
        url="https://www.law.cornell.edu/uscode/text/26/2053",
    ),
    "gross_estate": Citation(
        section="IRC §§2031–2033",
        description="Definition of gross estate.",
        url="https://www.law.cornell.edu/uscode/text/26/2031",
    ),
    "step_up_basis": Citation(
        section="IRC §1014",
        description="Step-up in basis to fair market value at decedent's death.",
        url="https://www.law.cornell.edu/uscode/text/26/1014",
    ),
    "community_property_double_step_up": Citation(
        section="IRC §1014(b)(6)",
        description="Both halves of community property receive a step-up at first spouse's death.",
        url="https://www.law.cornell.edu/uscode/text/26/1014",
    ),
    "ird_no_step_up": Citation(
        section="IRC §691; IRS Pub 559",
        description="Income in respect of a decedent retains carryover treatment; no §1014 step-up.",
        url="https://www.law.cornell.edu/uscode/text/26/691",
    ),
    "custodian_estate_inclusion": Citation(
        section="IRC §2038",
        description="Inclusion in donor's estate where donor retained powers (custodian-donor of UGMA/UTMA).",
        url="https://www.law.cornell.edu/uscode/text/26/2038",
    ),
    "gift_basis": Citation(
        section="IRC §1015",
        description="Donee takes donor's adjusted basis (carryover basis) for property acquired by gift.",
        url="https://www.law.cornell.edu/uscode/text/26/1015",
    ),
    # ---- GST tax ----
    "gst_exemption": Citation(
        section="IRC §2631",
        description="GST exemption allocation ($13.99M, 2025).",
        url="https://www.law.cornell.edu/uscode/text/26/2631",
    ),
    "skip_person": Citation(
        section="IRC §2613",
        description="Skip person definition (two or more generations below transferor).",
        url="https://www.law.cornell.edu/uscode/text/26/2613",
    ),
    "gst_rate": Citation(
        section="IRC §2641",
        description="GST tax rate (maximum federal estate tax rate).",
        url="https://www.law.cornell.edu/uscode/text/26/2641",
    ),
    # ---- Income tax mechanics ----
    "ordinary_rates": Citation(
        section="IRC §1; Rev. Proc. 2024-40",
        description="Ordinary income tax brackets for 2025.",
        url="https://www.irs.gov/pub/irs-drop/rp-24-40.pdf",
    ),
    "capital_gains_rates": Citation(
        section="IRC §1(h)",
        description="Long-term capital gains and qualified dividend preferential rates.",
        url="https://www.law.cornell.edu/uscode/text/26/1",
    ),
    "niit": Citation(
        section="IRC §1411",
        description="Net Investment Income Tax (3.8% on investment income above MAGI thresholds).",
        url="https://www.law.cornell.edu/uscode/text/26/1411",
    ),
    "kiddie_tax": Citation(
        section="IRC §1(g)",
        description="Unearned income of children taxed partly at parent's marginal rate.",
        url="https://www.law.cornell.edu/uscode/text/26/1",
    ),
    # ---- Retirement accounts ----
    "ira_earned_income": Citation(
        section="IRC §219(b)",
        description="IRA contribution limited by donee's earned income.",
        url="https://www.law.cornell.edu/uscode/text/26/219",
    ),
    "roth_earned_income": Citation(
        section="IRC §408A(c)(2)",
        description="Roth IRA contribution requires earned income.",
        url="https://www.law.cornell.edu/uscode/text/26/408A",
    ),
    "roth_qualified_distribution": Citation(
        section="IRC §408A(d)",
        description="Qualified Roth distributions are tax-free.",
        url="https://www.law.cornell.edu/uscode/text/26/408A",
    ),
    "secure_10_year": Citation(
        section="IRC §401(a)(9)(H)",
        description="SECURE Act 10-year distribution rule for non-spouse beneficiaries.",
        url="https://www.law.cornell.edu/uscode/text/26/401",
    ),
    "secure_2_529_roth": Citation(
        section="IRC §529(c)(3)(E)",
        description="SECURE 2.0 §126 — up to $35,000 lifetime 529 → Roth IRA rollover for beneficiary.",
        url="https://www.law.cornell.edu/uscode/text/26/529",
    ),
    "traditional_ira_distribution": Citation(
        section="IRC §408(d)",
        description="Traditional IRA distributions are ordinary income.",
        url="https://www.law.cornell.edu/uscode/text/26/408",
    ),
    # ---- Trump Account (OBBBA 2025) ----
    "trump_account_act": Citation(
        section="OBBBA §70404 (Pub. L. 119-21)",
        description="Trump Account established by the One Big Beautiful Bill Act, signed July 4, 2025.",
        url="https://www.congress.gov/bill/119th-congress/house-bill/1",
    ),
    "trump_account_federal_seed": Citation(
        section="OBBBA §70404(b)",
        description="$1,000 one-time federal seed deposit for U.S.-citizen children born 2025–2028.",
    ),
    "trump_account_parent_cap": Citation(
        section="OBBBA §70404(c)",
        description="$5,000/yr aggregate after-tax contribution cap from parents and employer combined.",
    ),
    "trump_account_distribution": Citation(
        section="OBBBA §70404(g); cf. IRC §72",
        description="Distributions after age 18 taxed as ordinary income on the earnings portion.",
    ),
    "trump_account_rollover": Citation(
        section="OBBBA §70404(h)",
        description="Rollover to traditional or Roth IRA permitted after age 18.",
    ),
    "trump_account_investment_restriction": Citation(
        section="OBBBA §70404(e)",
        description="Investments restricted to broad-based U.S. equity index funds.",
    ),

    # ---- 529 ----
    "529_growth": Citation(
        section="IRC §529(c)(1)",
        description="529 plan earnings grow federal-income-tax-free.",
        url="https://www.law.cornell.edu/uscode/text/26/529",
    ),
    "529_qualified_distribution": Citation(
        section="IRC §529(c)(3)",
        description="Qualified 529 distributions are excluded from gross income.",
        url="https://www.law.cornell.edu/uscode/text/26/529",
    ),
    "529_estate_exclusion": Citation(
        section="IRC §529(c)(4)",
        description="529 assets are excluded from donor's gross estate.",
        url="https://www.law.cornell.edu/uscode/text/26/529",
    ),
    "529_nonqualified_penalty": Citation(
        section="IRC §529(c)(6)",
        description="10% additional tax on earnings portion of non-qualified 529 withdrawals.",
        url="https://www.law.cornell.edu/uscode/text/26/529",
    ),
    # ---- State estate tax ----
    "ny_estate_cliff": Citation(
        section="NY Tax Law §§952, 954, 955",
        description="NY estate tax 'cliff' — exemption phases out completely above 105% threshold.",
        url="https://www.tax.ny.gov/forms/current-forms/et/et706i.htm",
        scope="state",
    ),
    "ny_3yr_gift_addback": Citation(
        section="NY Tax Law §954(a)(3)",
        description="NY adds back gifts made within three years of death.",
        url="https://www.tax.ny.gov/",
        scope="state",
    ),
    "ny_529_deduction": Citation(
        section="NY Tax Law §612(c)(32)",
        description="NY deduction for contributions to NY 529 Direct Plan ($5K / $10K MFJ).",
        url="https://www.tax.ny.gov/",
        scope="state",
    ),
    "il_estate_tax": Citation(
        section="35 ILCS 405/3; 405/5",
        description="Illinois estate tax — $4M exemption, no portability, not indexed.",
        url="https://tax.illinois.gov/",
        scope="state",
    ),
    "il_529_deduction": Citation(
        section="35 ILCS 5/203(a)(2)(Y)",
        description="Illinois deduction for Bright Start / Bright Directions 529 ($10K / $20K MFJ).",
        url="https://tax.illinois.gov/",
        scope="state",
    ),
    "tx_no_income_tax": Citation(
        section="Tex. Const. art. VIII, §24-a",
        description="Texas does not impose an individual income tax.",
        url="https://statutes.capitol.texas.gov/",
        scope="state",
    ),
    "tx_community_property": Citation(
        section="Tex. Fam. Code §3.002",
        description="Texas is a community property state — IRC §1014(b)(6) double step-up applies.",
        url="https://statutes.capitol.texas.gov/",
        scope="state",
    ),
    "tx_no_estate_tax": Citation(
        section="Tex. Tax Code Title 2 (repealed 2015)",
        description="Texas has no state estate or inheritance tax.",
        url="https://statutes.capitol.texas.gov/",
        scope="state",
    ),
}


@dataclass
class CitedAmount:
    """A monetary value annotated with its supporting citations."""

    label: str
    amount: "object"  # Decimal — typed loosely to avoid an engine.py import cycle
    citations: list[Citation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "amount": str(self.amount),
            "citations": [c.to_dict() for c in self.citations],
        }
