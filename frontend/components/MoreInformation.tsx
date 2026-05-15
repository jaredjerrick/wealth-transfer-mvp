"use client";
import { useState } from "react";
import { VEHICLES } from "../lib/vehicles";

type Tab = "vehicles" | "grat_trusts" | "gst" | "life_events";

export function MoreInformation() {
  const [tab, setTab] = useState<Tab>("vehicles");
  return (
    <div className="bg-white border border-slate-200 rounded-lg">
      <div className="border-b border-slate-200 px-4 py-3 flex items-center justify-between flex-wrap gap-2">
        <h3 className="font-semibold text-ink">More information</h3>
        <div className="flex gap-1 text-xs">
          <TabBtn current={tab} setter={setTab} value="vehicles">
            Account types
          </TabBtn>
          <TabBtn current={tab} setter={setTab} value="grat_trusts">
            GRATs &amp; trusts
          </TabBtn>
          <TabBtn current={tab} setter={setTab} value="gst">
            GST &amp; skipping a generation
          </TabBtn>
          <TabBtn current={tab} setter={setTab} value="life_events">
            Life events
          </TabBtn>
        </div>
      </div>
      <div className="p-4 text-sm text-ink/90 space-y-4">
        {tab === "vehicles" && <VehiclesPanel />}
        {tab === "grat_trusts" && <GRATTrustsPanel />}
        {tab === "gst" && <GSTPanel />}
        {tab === "life_events" && <LifeEventsPanel />}
      </div>
    </div>
  );
}

function TabBtn({
  current,
  setter,
  value,
  children,
}: {
  current: Tab;
  setter: (t: Tab) => void;
  value: Tab;
  children: React.ReactNode;
}) {
  const active = current === value;
  return (
    <button
      onClick={() => setter(value)}
      className={`px-2.5 py-1 rounded border ${
        active
          ? "bg-ink text-white border-ink"
          : "bg-white text-ink border-slate-200 hover:bg-slate-50"
      }`}
    >
      {children}
    </button>
  );
}

function VehiclesPanel() {
  return (
    <div className="space-y-4">
      <p className="text-xs text-muted">
        Plain-language summary of each account type modeled by the tool. Each section
        names the controlling IRC section so you can verify the tax treatment yourself.
        Use this as the audit trail for confirming that every account is being taxed
        appropriately.
      </p>
      {VEHICLES.map((v) => (
        <details key={v.key} className="rounded border border-slate-200">
          <summary className="px-3 py-2 cursor-pointer flex items-baseline justify-between bg-slate-50">
            <span className="font-medium">{v.strategyName}</span>
            <span className="text-xs text-muted">{v.ircSection}</span>
          </summary>
          <div className="px-3 py-3 space-y-2 text-sm">
            <p>{v.taxTreatment}</p>
            <dl className="grid grid-cols-[140px_1fr] gap-y-1 gap-x-3 text-xs">
              <dt className="text-muted">Annual cap</dt>
              <dd>{v.annualCap}</dd>
              <dt className="text-muted">Contributions</dt>
              <dd>{v.contributionTax}</dd>
              <dt className="text-muted">Growth</dt>
              <dd>{v.growthTax}</dd>
              <dt className="text-muted">Distributions</dt>
              <dd>{v.distributionTax}</dd>
              <dt className="text-muted">Estate inclusion</dt>
              <dd>{v.estateInclusion}</dd>
              <dt className="text-muted">Best fit</dt>
              <dd>{v.bestFor}</dd>
              <dt className="text-muted">Watch out</dt>
              <dd>{v.watchouts}</dd>
            </dl>
          </div>
        </details>
      ))}
    </div>
  );
}

function GRATTrustsPanel() {
  return (
    <div className="space-y-3 text-sm">
      <p className="text-xs text-muted">
        The tool doesn&rsquo;t simulate GRAT or trust mechanics yet — these mini-explainers
        are here so you understand the option, and can decide whether to involve an
        estate attorney to actually structure one.
      </p>

      <section className="border-l-4 border-blue-300 pl-3 space-y-1">
        <h4 className="font-medium">Zeroed-out (Walton) GRAT</h4>
        <p>
          A Grantor Retained Annuity Trust (IRC §2702) lets you put an appreciating asset
          into an irrevocable trust and receive a fixed annuity stream back over a term of
          years (often 2 years). If the asset out-earns the §7520 hurdle rate (a Treasury-
          published minimum interest rate), the excess passes to the remainder beneficiaries
          (your children or a trust for them) with <em>no gift tax</em>. The annuity is sized so
          the present value of the retained interest equals the contribution &mdash; hence
          &ldquo;zeroed-out.&rdquo;
        </p>
        <p className="text-xs text-muted">
          Best for: assets you expect to appreciate rapidly (private company stock,
          concentrated positions). Watch out: if you die during the term, the asset is pulled
          back into your estate under §2036.
        </p>
      </section>

      <section className="border-l-4 border-purple-300 pl-3 space-y-1">
        <h4 className="font-medium">Irrevocable Life Insurance Trust (ILIT)</h4>
        <p>
          An ILIT owns a life-insurance policy on the donor. The premiums are funded by gifts
          to the trust (often using the §2503(b) annual exclusion via &ldquo;Crummey&rdquo;
          withdrawal rights). At the donor&rsquo;s death, the policy pays out to the trust &mdash; outside
          the donor&rsquo;s estate &mdash; providing liquidity that the family can use to pay
          state estate tax or buy assets from the estate.
        </p>
        <p className="text-xs text-muted">
          Best for: donors above NY ($7.35M) or federal ($15.0M) thresholds whose estate is
          illiquid (e.g., a closely-held business).
        </p>
      </section>

      <section className="border-l-4 border-emerald-300 pl-3 space-y-1">
        <h4 className="font-medium">Dynasty Trust (GST trust)</h4>
        <p>
          A long-duration irrevocable trust designed to hold wealth for multiple generations
          while avoiding estate tax in each generation. The donor allocates §2631 GST
          exemption to the trust at funding, so future distributions to grandchildren and
          later generations are not subject to GST tax under §2641.
        </p>
        <p className="text-xs text-muted">
          State law matters: South Dakota, Delaware, Nevada, and Alaska allow trusts to last
          centuries. New York&rsquo;s rule against perpetuities is more restrictive. If
          you&rsquo;re planning a multi-generation strategy, jurisdiction selection is part
          of the conversation.
        </p>
      </section>

      <section className="border-l-4 border-amber-300 pl-3 space-y-1">
        <h4 className="font-medium">Spousal Lifetime Access Trust (SLAT)</h4>
        <p>
          A SLAT is an irrevocable trust funded by one spouse for the benefit of the other.
          The gift uses the donor-spouse&rsquo;s §2010 exemption and removes the assets from
          both spouses&rsquo; estates, while preserving practical access through distributions
          to the beneficiary spouse.
        </p>
        <p className="text-xs text-muted">
          Best for: married couples who want to lock in the current §2010 exemption (which is
          scheduled to drop in 2026 absent extension) while keeping a soft access channel.
        </p>
      </section>
    </div>
  );
}

function GSTPanel() {
  return (
    <div className="space-y-3 text-sm">
      <p>
        The generation-skipping transfer (GST) tax (IRC §§2611, 2631, 2641) layers on top of
        the estate and gift tax when wealth moves <em>two or more generations</em> below you &mdash;
        typically from grandparent to grandchild.
      </p>
      <p>
        The rationale is simple: without the GST tax, a billionaire could leave assets directly
        to a grandchild and skip the estate tax that would have applied at the child&rsquo;s
        death. Congress&rsquo;s response was a flat tax at the maximum federal estate-tax rate
        (currently 40%) on any &ldquo;skip&rdquo; transfer above the donor&rsquo;s remaining
        GST exemption.
      </p>
      <p>
        The good news: every donor gets a GST exemption equal to the §2010 basic exclusion
        ($15.0M for 2026). Allocate it to a dynasty trust at funding, and decades of
        compounding inside the trust can pass through multiple generations entirely free of
        transfer tax.
      </p>
      <ul className="list-disc list-inside space-y-1 text-xs text-muted">
        <li>
          Toggle the &ldquo;skip person&rdquo; checkbox above to see how the GST tax would
          alter the after-tax math for each strategy.
        </li>
        <li>
          Most 529, UTMA, and Roth-IRA contributions to a grandchild qualify for the
          §2642(c) GST annual exclusion (mirrors the §2503(b) gift annual exclusion), so
          regular contributions usually do not consume your GST exemption.
        </li>
        <li>
          The largest GST-leveraged tool is a dynasty trust &mdash; see the GRATs &amp;
          trusts tab.
        </li>
      </ul>
    </div>
  );
}

function LifeEventsPanel() {
  return (
    <div className="space-y-3 text-sm">
      <p>
        Three transfer-tax milestones that come up for almost every family. Each one
        interacts with which vehicle you should be funding now.
      </p>

      <section>
        <h4 className="font-medium">College (around age 18)</h4>
        <p>
          The 529 is purpose-built. Qualified higher-education distributions are tax-free
          under §529(c)(3) and the asset is excluded from your estate under §529(c)(4).
          SECURE 2.0 §126 also lets up to $35,000 of unused 529 corpus roll to a Roth IRA
          for the beneficiary.
        </p>
      </section>

      <section>
        <h4 className="font-medium">Wedding (typically late 20s)</h4>
        <p>
          §2503(e) <em>does not</em> cover weddings &mdash; that section is limited to
          tuition and medical expenses paid directly to the provider. Plan to use the
          §2503(b) annual exclusion ($19,000/donor/donee for 2026), or dip into the §2010
          lifetime exemption. UTMA assets can also be used once the child reaches the age
          of majority (21 in NY / IL / TX).
        </p>
      </section>

      <section>
        <h4 className="font-medium">First home (typically late 20s to early 30s)</h4>
        <p>
          A Roth IRA allows a $10,000 lifetime first-home distribution without the 10%
          penalty under §72(t)(2)(F). The annual exclusion can fund the rest. If you&rsquo;re
          planning to gift a large down-payment, consider whether you want the child to hold
          the cash (UTMA / annual-exclusion gift) or whether the parent should hold title
          (taxable brokerage), which has different control implications.
        </p>
      </section>
    </div>
  );
}
