"use client";

import { useEffect, useState } from "react";
import { InputForm } from "../components/InputForm";
import { ComparisonTable } from "../components/ComparisonTable";
import { AccumulationChart } from "../components/AccumulationChart";
import { TaxDragWaterfall } from "../components/TaxDragWaterfall";
import { TradeoffMatrix } from "../components/TradeoffMatrix";
import { RecommendationsPanel } from "../components/RecommendationsPanel";
import { TaxExplanations } from "../components/TaxExplanations";
import { MoreInformation } from "../components/MoreInformation";
import { compareStrategies, downloadPdf, fetchRulesVersion } from "../lib/api";
import type { CompareResultDto, DonorInputsPayload } from "../lib/types";

const DEFAULTS: DonorInputsPayload = {
  donor_age: 45,
  donor_gross_income_agi: "250000",
  filing_status: "mfj",
  state: "NY",
  donor_net_worth: "5000000",
  spouse_present: true,
  num_children: 1,
  planned_retirement_age: 65,
  child_age: 5,
  child_earned_income: "5000",
  child_expects_college: true,
  existing_balances: {},
  investment_horizon_years: 18,
  annual_contribution: "19000",
  expected_pretax_return: "0.07",
  inflation_rate: "0.025",
  elect_529_five_year: false,
  elect_gift_splitting: false,
  charitable_bequest_pct: "0",
  elect_skip_generation: false,
  plan_pay_college: true,
  plan_pay_wedding: false,
  plan_pay_first_home: false,
  est_college_cost_today: "150000",
  est_wedding_cost_today: "35000",
  est_first_home_help_today: "75000",
};

export default function Page() {
  const [payload, setPayload] = useState<DonorInputsPayload>(DEFAULTS);
  const [result, setResult] = useState<CompareResultDto | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [rulesVersion, setRulesVersion] = useState<{
    tax_year: number;
    last_updated: string;
    source: string;
    bluej_enabled: boolean;
    aiwyn_validator_enabled: boolean;
  } | null>(null);

  useEffect(() => {
    fetchRulesVersion().then(setRulesVersion).catch(() => {});
  }, []);

  async function onSubmit(p: DonorInputsPayload) {
    setPayload(p);
    setLoading(true);
    setError(null);
    try {
      const r = await compareStrategies(p);
      setResult(r);
    } catch (e: any) {
      setError(e.message || "Comparison failed");
    } finally {
      setLoading(false);
    }
  }

  async function onPdf() {
    try {
      const blob = await downloadPdf(payload);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "strategy_brief.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e.message || "PDF download failed");
    }
  }

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-ink">
              Wealth Transfer Strategy Comparison
            </h1>
            <p className="text-xs text-muted mt-0.5">
              Educational model · not tax or legal advice · every number traces to an IRC citation
            </p>
          </div>
          {result && (
            <button
              onClick={onPdf}
              className="text-sm bg-ink text-white px-3 py-1.5 rounded hover:bg-slate-800"
            >
              Download Strategy Brief (PDF)
            </button>
          )}
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 space-y-4">
          <InputForm initial={DEFAULTS} onSubmit={onSubmit} loading={loading} />
          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-3 text-sm text-red-800">
              {error}
            </div>
          )}
        </div>

        <div className="lg:col-span-8 space-y-6">
          {!result && !loading && (
            <div className="bg-white border border-slate-200 rounded-lg p-8 text-center text-muted text-sm">
              Enter planning inputs and click <span className="font-medium">Compare strategies</span>.
              <br />
              All six vehicles will be modeled across the federal and state regime for {payload.state}.
            </div>
          )}
          {result && (
            <>
              <ComparisonTable data={result} />
              <RecommendationsPanel data={result} />
              <TaxExplanations data={result} />
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                <AccumulationChart data={result} />
                <TaxDragWaterfall data={result} />
              </div>
              <TradeoffMatrix data={result} />
            </>
          )}
          <MoreInformation />
        </div>
      </main>

      <footer className="border-t border-slate-200 bg-white mt-10">
        <div className="max-w-7xl mx-auto px-6 py-3 text-xs text-muted flex flex-wrap justify-between items-center gap-2">
          <div>
            Rules version:{" "}
            {rulesVersion
              ? `${rulesVersion.tax_year} (updated ${rulesVersion.last_updated})`
              : "—"}
          </div>
          <div className="flex gap-3">
            {rulesVersion?.aiwyn_validator_enabled && (
              <span className="text-emerald-700">Aiwyn validator: on</span>
            )}
            <span className={rulesVersion?.bluej_enabled ? "text-emerald-700" : "text-slate-400"}>
              Blue J: {rulesVersion?.bluej_enabled ? "on" : "off"}
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
