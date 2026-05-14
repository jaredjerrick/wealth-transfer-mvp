// Display metadata for each modeled vehicle. The `key` matches the backend
// `engine.inputs.VehicleKey` enum, and `strategyName` matches the
// `Strategy.name` value the engine returns in `StrategyResult.strategy_name`
// so the UI can join a vehicle key to its engine row.

import type { VehicleKey } from "./types";

export interface VehicleInfo {
  key: VehicleKey;
  strategyName: string;       // display name as used by the engine
  shortLabel: string;         // tighter label for chips
  ircSection: string;         // primary controlling section, for the More Info card
  annualCap: string;          // human description of the annual cap
  taxTreatment: string;       // 1–2 sentence plain-language summary
  contributionTax: string;    // tax treatment of contributions
  growthTax: string;          // tax treatment of growth
  distributionTax: string;    // tax treatment of distributions
  estateInclusion: string;    // is the asset included in the donor's estate?
  bestFor: string;            // who is this vehicle best suited for
  watchouts: string;          // common gotchas
}

export const VEHICLES: VehicleInfo[] = [
  {
    key: "section_529",
    strategyName: "529 Plan",
    shortLabel: "529",
    ircSection: "IRC §529",
    annualCap:
      "No federal annual cap (subject to the §2503(b) annual exclusion to avoid gift-tax filing). Each state plan enforces a per-beneficiary aggregate cap, typically $500K–$550K.",
    taxTreatment:
      "Tax-advantaged education savings account. Money grows tax-free and qualified withdrawals are tax-free.",
    contributionTax:
      "After-tax dollars at the federal level. Many states (including NY and IL) provide a state income-tax deduction up to a cap. Texas has no state income tax, so no state deduction.",
    growthTax: "Tax-free growth under IRC §529(c)(1).",
    distributionTax:
      "Tax-free if used for qualified higher-education / K-12 expenses under §529(c)(3). Non-qualified withdrawals face ordinary income on the earnings portion plus a 10% additional tax under §529(c)(6). SECURE 2.0 §126 also permits up to $35,000 lifetime to roll to a Roth IRA for the beneficiary.",
    estateInclusion:
      "Excluded from the donor's gross estate under §529(c)(4) — the rare case where the donor retains control without inclusion.",
    bestFor:
      "Parents whose primary goal is funding college / K–12 education, especially in NY or IL where the state deduction stacks on top of federal tax-free growth.",
    watchouts:
      "Non-qualified withdrawals are penalized. Aggressive frontloading should use the §529(c)(2)(B) 5-year forward election to avoid burning lifetime exemption.",
  },
  {
    key: "roth_ira",
    strategyName: "Roth IRA (Custodial)",
    shortLabel: "Roth IRA",
    ircSection: "IRC §408A",
    annualCap:
      "Lesser of $7,000 (2025) or the child's earned income. Requires the child to have W-2 or self-employment income under §408A(c)(2).",
    taxTreatment:
      "Funded with after-tax dollars. Growth and qualified withdrawals are federal-income-tax-free.",
    contributionTax: "After-tax — no upfront deduction.",
    growthTax: "Tax-free.",
    distributionTax:
      "Qualified distributions are tax-free under §408A(d) (account at least 5 years old + age 59½, death, disability, or up to $10K first-home purchase). Earnings withdrawn early may face ordinary income + 10% penalty.",
    estateInclusion:
      "Not includible in the donor's gross estate — the contribution is a completed gift to the child's account from day one.",
    bestFor:
      "Young children with earned income (e.g., model work, family-business wages). Highest per-dollar after-tax wealth on long horizons.",
    watchouts:
      "The earned-income requirement is a hard block. Donors cannot just 'gift' contributions absent the child's actual wages.",
  },
  {
    key: "traditional_ira",
    strategyName: "Traditional IRA",
    shortLabel: "Trad IRA",
    ircSection: "IRC §408 / §219",
    annualCap:
      "Lesser of $7,000 (2025) or the child's earned income. Requires the child to have earned income under §219(b).",
    taxTreatment:
      "Tax-deductible contributions, tax-deferred growth, ordinary income tax on distributions.",
    contributionTax:
      "Deductible on the child's return, but the deduction value is small when the child's marginal rate is low.",
    growthTax: "Tax-deferred.",
    distributionTax:
      "Ordinary income tax on distributions under §408(d). No §1014 basis step-up at death — embedded gain stays ordinary income (IRD under §691). Non-spouse beneficiaries are subject to the SECURE Act §401(a)(9)(H) 10-year rule.",
    estateInclusion:
      "Not includible in the donor's estate (the gift was completed when the child funded the IRA), but the income tax embedded in the account passes through to the heir as IRD.",
    bestFor:
      "Children who expect to be in a *lower* lifetime tax bracket than their parents — rare for high-earning families.",
    watchouts:
      "On long horizons the Roth almost always beats the Traditional once you compare on an after-tax basis at distribution.",
  },
  {
    key: "ugma_utma",
    strategyName: "UGMA/UTMA",
    shortLabel: "UGMA/UTMA",
    ircSection: "State UGMA/UTMA acts; IRC §1(g) kiddie tax",
    annualCap:
      "No federal cap; contributions use the §2503(b) annual exclusion ($19,000/donor/donee for 2025).",
    taxTreatment:
      "Custodial brokerage account held in the child's name. Income on the account is the child's, subject to the kiddie tax (§1(g)).",
    contributionTax:
      "After-tax. Contributions are completed gifts under §2511 and qualify for the §2503(b) annual exclusion.",
    growthTax:
      "Annual dividends and realized gains taxed to the child each year. While the child is under 19 (or under 24 if a full-time student), unearned income above $2,700 is taxed at the parent's marginal rate.",
    distributionTax:
      "Carryover basis (§1015) — the child inherits the donor's basis. Embedded gain is taxed when the child sells, typically at the child's lower bracket once they age out.",
    estateInclusion:
      "Generally not includible in the donor's estate — UNLESS the donor also serves as the custodian and dies before the age of majority, in which case §2038 pulls the account back in.",
    bestFor:
      "Parents who want flexibility (any-purpose) and don't mind the loss of control once the child reaches the state age of majority (21 in NY/IL/TX).",
    watchouts:
      "At majority the asset belongs to the child outright. A child who suddenly inherits a 6-figure brokerage account at 21 may not spend it the way the parents would. Also: financial-aid hit on FAFSA.",
  },
  {
    key: "trump_account",
    strategyName: "Trump Account",
    shortLabel: "Trump Acct",
    ircSection: "OBBBA §70404 (Pub. L. 119-21)",
    annualCap:
      "$5,000/yr aggregate from parents + employer combined. Plus a one-time $1,000 federal seed for U.S.-citizen children born 2025–2028.",
    taxTreatment:
      "After-tax contributions, tax-deferred growth, ordinary income tax on the earnings portion at distribution.",
    contributionTax: "After-tax — no deduction.",
    growthTax: "Tax-deferred.",
    distributionTax:
      "Earnings portion is taxed as ordinary income at the beneficiary's rate; principal is basis-recovered tax-free. May be rolled to a Traditional or Roth IRA after age 18 under §70404(h).",
    estateInclusion:
      "Not includible in donor's estate — contributions are completed gifts within the §2503(b) annual exclusion.",
    bestFor:
      "Parents of children born 2025–2028 who want to capture the $1,000 federal seed. Best paired with other vehicles, since the $5,000 cap is the binding constraint at meaningful contribution levels.",
    watchouts:
      "Restricted to broad-based U.S. equity index funds (§70404(e)) — no asset-class diversification. No access before age 18. Treasury regulations were still maturing as of 2025.",
  },
  {
    key: "taxable_brokerage",
    strategyName: "Taxable Brokerage",
    shortLabel: "Taxable",
    ircSection: "IRC §§1, 1(h), 1411 (general income & cap-gains regime)",
    annualCap: "None.",
    taxTreatment:
      "Standard after-tax brokerage account. Dividends and realized gains are taxed each year; the §1014 basis step-up at death forgives embedded gain.",
    contributionTax: "After-tax.",
    growthTax:
      "Annual drag on dividends and realized gains: qualified dividends and LTCG at the preferential rate; ordinary dividends and short-term gains at the donor's marginal; NIIT (3.8%) if AGI exceeds §1411 thresholds.",
    distributionTax:
      "At the donor's death, basis steps up to fair market value under §1014 — embedded appreciation is forgiven for the heir. (Texas community property gets the double step-up under §1014(b)(6) for married donors.)",
    estateInclusion:
      "Fully includible under §§2031–2033. Estate tax applies above the §2010 unified credit, with state estate tax layered on for NY (cliff) and IL ($4M).",
    bestFor:
      "Parents who want maximum flexibility and liquidity, and whose estate is well below the federal §2010 exclusion ($13.99M, 2025).",
    watchouts:
      "On large estates, the federal + state estate tax bite can be material — the §1014 step-up is a powerful saving but only on the *income tax* side.",
  },
  {
    key: "hold_until_death",
    strategyName: "Hold Until Death",
    shortLabel: "Hold to Death",
    ircSection: "IRC §1014 + §§2031–2033",
    annualCap: "None.",
    taxTreatment:
      "Same as Taxable Brokerage, but the donor commits to buy-and-hold (no realized gains during life) to maximize the §1014 basis step-up at death.",
    contributionTax: "After-tax.",
    growthTax:
      "Near-zero drag during accumulation — only unavoidable qualified-dividend tax.",
    distributionTax:
      "§1014 step-up at death erases embedded gain for the heir; the rest mirrors a taxable account.",
    estateInclusion: "Fully includible under §§2031–2033.",
    bestFor:
      "Parents whose donor-controlled assets are below the state and federal estate-tax thresholds, where the income-tax saving from the step-up dominates.",
    watchouts:
      "If your estate is near or above the NY ($7.16M) or federal ($13.99M) thresholds, the estate-tax overhang can dwarf the income-tax saving.",
  },
];

// Lookup map by key.
export const VEHICLES_BY_KEY: Record<VehicleKey, VehicleInfo> = Object.fromEntries(
  VEHICLES.map((v) => [v.key, v])
) as Record<VehicleKey, VehicleInfo>;

export function vehicleByStrategyName(name: string): VehicleInfo | undefined {
  return VEHICLES.find((v) => v.strategyName === name);
}
