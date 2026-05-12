"use client";
import { useState } from "react";
import type { DonorInputsPayload } from "../lib/types";

interface Props {
  initial: DonorInputsPayload;
  onSubmit: (payload: DonorInputsPayload) => void;
  loading: boolean;
}

export function InputForm({ initial, onSubmit, loading }: Props) {
  const [v, setV] = useState<DonorInputsPayload>(initial);

  function update<K extends keyof DonorInputsPayload>(k: K, val: DonorInputsPayload[K]) {
    setV((prev) => ({ ...prev, [k]: val }));
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit(v);
  }

  return (
    <form onSubmit={submit} className="bg-white border border-slate-200 rounded-lg p-6 space-y-5">
      <h2 className="text-lg font-semibold text-ink">Planning inputs</h2>

      <fieldset className="grid grid-cols-2 gap-3">
        <legend className="col-span-2 text-xs font-semibold text-muted uppercase tracking-wide">Donor profile</legend>
        <label className="text-sm">
          <span className="block text-muted">Age</span>
          <input
            type="number"
            min={18}
            max={110}
            value={v.donor_age}
            onChange={(e) => update("donor_age", Number(e.target.value))}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm">
          <span className="block text-muted">AGI</span>
          <input
            type="text"
            value={v.donor_gross_income_agi}
            onChange={(e) => update("donor_gross_income_agi", e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm">
          <span className="block text-muted">Filing status</span>
          <select
            value={v.filing_status}
            onChange={(e) => update("filing_status", e.target.value as DonorInputsPayload["filing_status"])}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1 bg-white"
          >
            <option value="single">Single</option>
            <option value="mfj">Married filing jointly</option>
            <option value="mfs">Married filing separately</option>
            <option value="hoh">Head of household</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="block text-muted">State of domicile</span>
          <select
            value={v.state}
            onChange={(e) => update("state", e.target.value as DonorInputsPayload["state"])}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1 bg-white"
          >
            <option value="NY">New York</option>
            <option value="IL">Illinois</option>
            <option value="TX">Texas</option>
          </select>
        </label>
        <label className="text-sm">
          <span className="block text-muted">Net worth</span>
          <input
            type="text"
            value={v.donor_net_worth}
            onChange={(e) => update("donor_net_worth", e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm flex items-center gap-2 mt-5">
          <input
            type="checkbox"
            checked={v.spouse_present}
            onChange={(e) => update("spouse_present", e.target.checked)}
          />
          <span>Spouse present</span>
        </label>
      </fieldset>

      <fieldset className="grid grid-cols-2 gap-3">
        <legend className="col-span-2 text-xs font-semibold text-muted uppercase tracking-wide">Beneficiary</legend>
        <label className="text-sm">
          <span className="block text-muted">Child's age</span>
          <input
            type="number"
            min={0}
            max={25}
            value={v.child_age}
            onChange={(e) => update("child_age", Number(e.target.value))}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm">
          <span className="block text-muted">Earned income (unlocks Roth/Traditional IRA)</span>
          <input
            type="text"
            value={v.child_earned_income}
            onChange={(e) => update("child_earned_income", e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
      </fieldset>

      <fieldset className="grid grid-cols-2 gap-3">
        <legend className="col-span-2 text-xs font-semibold text-muted uppercase tracking-wide">Planning horizon</legend>
        <label className="text-sm">
          <span className="block text-muted">Horizon (years)</span>
          <input
            type="number"
            min={1}
            max={60}
            value={v.investment_horizon_years}
            onChange={(e) => update("investment_horizon_years", Number(e.target.value))}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm">
          <span className="block text-muted">Annual contribution</span>
          <input
            type="text"
            value={v.annual_contribution}
            onChange={(e) => update("annual_contribution", e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm">
          <span className="block text-muted">Expected pre-tax return</span>
          <input
            type="text"
            value={v.expected_pretax_return}
            onChange={(e) => update("expected_pretax_return", e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm flex items-center gap-2 mt-5">
          <input
            type="checkbox"
            checked={!!v.elect_529_five_year}
            onChange={(e) => update("elect_529_five_year", e.target.checked)}
          />
          <span>5-year §529(c)(2)(B) election</span>
        </label>
      </fieldset>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-ink text-white font-medium rounded py-2 hover:bg-slate-800 disabled:opacity-50"
      >
        {loading ? "Computing…" : "Compare strategies"}
      </button>
    </form>
  );
}
