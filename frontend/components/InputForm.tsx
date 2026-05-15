"use client";
import { useEffect, useMemo, useState } from "react";
import type {
  AllocationItem,
  DonorInputsPayload,
  VehicleKey,
} from "../lib/types";
import { displayCurrencyInput, parseCurrencyInput, formatMoney } from "../lib/api";
import { PRESETS, DEFAULT_PRESET_ID } from "../lib/presets";
import { VEHICLES } from "../lib/vehicles";

interface Props {
  initial: DonorInputsPayload;
  onSubmit: (payload: DonorInputsPayload) => void;
  loading: boolean;
}

// A small input that always renders the value as `$1,234` while preserving
// the raw numeric string that the engine expects.
function CurrencyInput({
  value,
  onChange,
  className,
}: {
  value: string;
  onChange: (v: string) => void;
  className?: string;
}) {
  return (
    <input
      type="text"
      inputMode="decimal"
      value={displayCurrencyInput(value)}
      onChange={(e) => onChange(parseCurrencyInput(e.target.value))}
      className={className}
    />
  );
}

export function InputForm({ initial, onSubmit, loading }: Props) {
  const [v, setV] = useState<DonorInputsPayload>(initial);
  const [presetId, setPresetId] = useState<string>(DEFAULT_PRESET_ID);

  // Derive an allocation array from the chosen preset + the current annual
  // contribution. "Custom" lets the user edit per-vehicle dollars directly.
  const initialAllocation: AllocationItem[] = useMemo(() => {
    const preset = PRESETS.find((p) => p.id === DEFAULT_PRESET_ID);
    if (!preset || preset.weights.length === 0) return [];
    const annual = parseFloat(initial.annual_contribution || "0");
    return preset.weights.map((w) => ({
      vehicle: w.vehicle,
      annual_amount: (annual * w.weight).toFixed(0),
    }));
  }, [initial.annual_contribution]);

  const [allocation, setAllocation] = useState<AllocationItem[]>(initialAllocation);

  function update<K extends keyof DonorInputsPayload>(k: K, val: DonorInputsPayload[K]) {
    setV((prev) => ({ ...prev, [k]: val }));
  }

  function updateExistingBalance(vehicle: VehicleKey, val: string) {
    setV((prev) => ({
      ...prev,
      existing_balances: { ...(prev.existing_balances ?? {}), [vehicle]: val },
    }));
  }

  function applyPreset(id: string) {
    setPresetId(id);
    // The rebalance effect below handles re-deriving the allocation rows for
    // non-custom presets from {presetId, annual_contribution}. We only need
    // special handling here for "custom": seed an empty allocation with a
    // starter row so the user has something to edit from.
    if (id === "custom" && allocation.length === 0) {
      setAllocation([{ vehicle: "section_529", annual_amount: "0" }]);
    }
  }

  // Live rebalance: whenever the annual contribution changes (or the user
  // picks a different non-custom preset), redistribute the per-vehicle
  // dollars according to the preset weights. "Custom" is intentionally
  // excluded so manual edits aren't clobbered.
  useEffect(() => {
    if (presetId === "custom") return;
    const preset = PRESETS.find((p) => p.id === presetId);
    if (!preset || preset.weights.length === 0) return;
    const annual = parseFloat(v.annual_contribution || "0");
    setAllocation(
      preset.weights.map((w) => ({
        vehicle: w.vehicle,
        annual_amount: (annual * w.weight).toFixed(0),
      }))
    );
  }, [v.annual_contribution, presetId]);

  function updateAllocationRow(i: number, patch: Partial<AllocationItem>) {
    setAllocation((rows) => rows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }

  function addAllocationRow() {
    setAllocation((rows) => [
      ...rows,
      { vehicle: "section_529", annual_amount: "0" },
    ]);
  }

  function removeAllocationRow(i: number) {
    setAllocation((rows) => rows.filter((_, idx) => idx !== i));
  }

  const totalAllocated = useMemo(
    () => allocation.reduce((s, a) => s + (parseFloat(a.annual_amount || "0") || 0), 0),
    [allocation]
  );

  function submit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      ...v,
      allocation: allocation.length > 0 ? allocation : null,
    });
  }

  return (
    <form onSubmit={submit} className="bg-white border border-slate-200 rounded-lg p-6 space-y-5">
      <h2 className="text-lg font-semibold text-ink">Planning inputs</h2>

      {/* ===== Donor profile ===== */}
      <fieldset className="grid grid-cols-2 gap-3">
        <legend className="col-span-2 text-xs font-semibold text-muted uppercase tracking-wide">
          Donor profile
        </legend>
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
          <CurrencyInput
            value={v.donor_gross_income_agi}
            onChange={(val) => update("donor_gross_income_agi", val)}
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
          <CurrencyInput
            value={v.donor_net_worth}
            onChange={(val) => update("donor_net_worth", val)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm">
          <span className="block text-muted">Number of children</span>
          <input
            type="number"
            min={1}
            max={10}
            value={v.num_children ?? 1}
            onChange={(e) => update("num_children", Number(e.target.value))}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm">
          <span className="block text-muted">Planned retirement age (optional)</span>
          <input
            type="number"
            min={40}
            max={85}
            value={v.planned_retirement_age ?? ""}
            onChange={(e) =>
              update(
                "planned_retirement_age",
                e.target.value === "" ? null : Number(e.target.value)
              )
            }
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

      {/* ===== Beneficiary ===== */}
      <fieldset className="grid grid-cols-2 gap-3">
        <legend className="col-span-2 text-xs font-semibold text-muted uppercase tracking-wide">
          Beneficiary
        </legend>
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
          <span className="block text-muted">Earned income (unlocks Roth / Traditional IRA)</span>
          <CurrencyInput
            value={v.child_earned_income}
            onChange={(val) => update("child_earned_income", val)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
        <label className="text-sm col-span-2 flex items-center gap-2">
          <input
            type="checkbox"
            checked={v.child_expects_college ?? true}
            onChange={(e) => update("child_expects_college", e.target.checked)}
          />
          <span>Expects to attend college</span>
        </label>

        <fieldset className="col-span-2 mt-2">
          <legend className="text-xs font-medium text-muted">Existing balances (optional)</legend>
          <div className="mt-1 grid grid-cols-2 gap-2">
            {VEHICLES.map((veh) => (
              <label key={veh.key} className="text-xs">
                <span className="block text-muted">{veh.shortLabel}</span>
                <CurrencyInput
                  value={v.existing_balances?.[veh.key] ?? ""}
                  onChange={(val) => updateExistingBalance(veh.key, val)}
                  className="mt-0.5 w-full rounded border border-slate-300 px-2 py-1"
                />
              </label>
            ))}
          </div>
        </fieldset>
      </fieldset>

      {/* ===== Horizon and contributions ===== */}
      <fieldset className="grid grid-cols-2 gap-3">
        <legend className="col-span-2 text-xs font-semibold text-muted uppercase tracking-wide">
          Planning horizon
        </legend>
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
          <CurrencyInput
            value={v.annual_contribution}
            onChange={(val) => update("annual_contribution", val)}
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

      {/* ===== Diversified allocation ===== */}
      <fieldset className="space-y-2">
        <legend className="text-xs font-semibold text-muted uppercase tracking-wide">
          Diversification (optional)
        </legend>
        <p className="text-xs text-muted">
          Split your annual contribution across vehicles. We&rsquo;ll model a
          &ldquo;Diversified Portfolio&rdquo; row alongside the individual strategies.
        </p>
        <select
          value={presetId}
          onChange={(e) => applyPreset(e.target.value)}
          className="text-sm rounded border border-slate-300 px-2 py-1 bg-white"
        >
          {PRESETS.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} — {p.tagline}
            </option>
          ))}
        </select>
        <p className="text-xs text-slate-500 italic">
          {PRESETS.find((p) => p.id === presetId)?.description}
        </p>
        {allocation.length > 0 && (
          <div className="space-y-1">
            {allocation.map((row, i) => (
              <div key={i} className="grid grid-cols-[1fr_auto_auto] gap-2 items-center">
                <select
                  value={row.vehicle}
                  onChange={(e) =>
                    updateAllocationRow(i, { vehicle: e.target.value as VehicleKey })
                  }
                  className="text-sm rounded border border-slate-300 px-2 py-1 bg-white"
                >
                  {VEHICLES.map((veh) => (
                    <option key={veh.key} value={veh.key}>
                      {veh.shortLabel}
                    </option>
                  ))}
                </select>
                <CurrencyInput
                  value={row.annual_amount}
                  onChange={(val) => updateAllocationRow(i, { annual_amount: val })}
                  className="w-28 text-sm rounded border border-slate-300 px-2 py-1"
                />
                <button
                  type="button"
                  onClick={() => removeAllocationRow(i)}
                  className="text-xs text-red-600 hover:underline"
                >
                  Remove
                </button>
              </div>
            ))}
            <div className="flex items-center justify-between text-xs">
              <button
                type="button"
                onClick={addAllocationRow}
                className="text-accent hover:text-accent-hover hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring rounded"
              >
                + Add vehicle
              </button>
              <span className="text-muted">
                Allocated: <span className="font-medium">{formatMoney(totalAllocated)}</span> / yr
                {parseFloat(v.annual_contribution || "0") > 0 && (
                  <>
                    {" "}
                    (target {formatMoney(parseFloat(v.annual_contribution))})
                  </>
                )}
              </span>
            </div>
          </div>
        )}
      </fieldset>

      {/* ===== Life events ===== */}
      <fieldset className="space-y-2">
        <legend className="text-xs font-semibold text-muted uppercase tracking-wide">
          Life-event decisions
        </legend>
        <p className="text-xs text-muted">
          These shape the recommendations panel — they don&rsquo;t change strategy math directly.
        </p>
        <label className="text-sm flex items-center gap-2">
          <input
            type="checkbox"
            checked={v.plan_pay_college ?? true}
            onChange={(e) => update("plan_pay_college", e.target.checked)}
          />
          <span>Plan to pay for college</span>
        </label>
        {v.plan_pay_college && (
          <label className="text-xs block ml-6">
            <span className="block text-muted">Total college cost (today&apos;s dollars)</span>
            <CurrencyInput
              value={v.est_college_cost_today ?? "150000"}
              onChange={(val) => update("est_college_cost_today", val)}
              className="mt-0.5 w-40 rounded border border-slate-300 px-2 py-1"
            />
          </label>
        )}
        <label className="text-sm flex items-center gap-2">
          <input
            type="checkbox"
            checked={v.plan_pay_wedding ?? false}
            onChange={(e) => update("plan_pay_wedding", e.target.checked)}
          />
          <span>Plan to pay for child&apos;s wedding</span>
        </label>
        {v.plan_pay_wedding && (
          <label className="text-xs block ml-6">
            <span className="block text-muted">Wedding budget (today&apos;s dollars)</span>
            <CurrencyInput
              value={v.est_wedding_cost_today ?? "35000"}
              onChange={(val) => update("est_wedding_cost_today", val)}
              className="mt-0.5 w-40 rounded border border-slate-300 px-2 py-1"
            />
          </label>
        )}
        <label className="text-sm flex items-center gap-2">
          <input
            type="checkbox"
            checked={v.plan_pay_first_home ?? false}
            onChange={(e) => update("plan_pay_first_home", e.target.checked)}
          />
          <span>Plan to help with child&apos;s first home</span>
        </label>
        {v.plan_pay_first_home && (
          <label className="text-xs block ml-6">
            <span className="block text-muted">First-home help (today&apos;s dollars)</span>
            <CurrencyInput
              value={v.est_first_home_help_today ?? "75000"}
              onChange={(val) => update("est_first_home_help_today", val)}
              className="mt-0.5 w-40 rounded border border-slate-300 px-2 py-1"
            />
          </label>
        )}
      </fieldset>

      {/* ===== Estate / GST toggles ===== */}
      <fieldset className="space-y-2">
        <legend className="text-xs font-semibold text-muted uppercase tracking-wide">
          Estate planning toggles
        </legend>
        <label className="text-sm flex items-center gap-2">
          <input
            type="checkbox"
            checked={!!v.elect_gift_splitting}
            onChange={(e) => update("elect_gift_splitting", e.target.checked)}
            disabled={!v.spouse_present}
          />
          <span className={v.spouse_present ? "" : "text-slate-400"}>
            Elect spousal gift-splitting (§2513)
          </span>
        </label>
        <label className="text-sm flex items-center gap-2">
          <input
            type="checkbox"
            checked={!!v.elect_skip_generation}
            onChange={(e) => update("elect_skip_generation", e.target.checked)}
          />
          <span>Recipient is a skip person (grandchild) — apply GST tax</span>
        </label>
      </fieldset>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-accent text-white font-medium rounded-md py-2.5 hover:bg-accent-hover focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-ring focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? "Computing…" : "Compare strategies"}
      </button>
    </form>
  );
}
