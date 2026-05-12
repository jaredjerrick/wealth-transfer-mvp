"use client";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { CompareResultDto } from "../lib/types";

// Subjective heuristic ratings (0–5) for non-numeric tradeoffs.
// These are hard-coded best-of-knowledge ratings, not LLM output.
const ATTRIBUTES: Record<string, Record<string, number>> = {
  "Donor control": {
    "Taxable Brokerage": 5,
    "Hold Until Death": 5,
    "529 Plan": 4,
    "UGMA/UTMA": 1,
    "Traditional IRA": 1,
    "Roth IRA (Custodial)": 1,
    "Trump Account": 2,
  },
  "Tax efficiency": {
    "Taxable Brokerage": 2,
    "Hold Until Death": 4,
    "529 Plan": 5,
    "UGMA/UTMA": 2,
    "Traditional IRA": 2,
    "Roth IRA (Custodial)": 5,
    "Trump Account": 3,
  },
  "Flexibility (non-edu use)": {
    "Taxable Brokerage": 5,
    "Hold Until Death": 5,
    "529 Plan": 2,
    "UGMA/UTMA": 4,
    "Traditional IRA": 2,
    "Roth IRA (Custodial)": 2,
    "Trump Account": 3,
  },
  "Beneficiary access age": {
    "Taxable Brokerage": 5,
    "Hold Until Death": 5,
    "529 Plan": 3,
    "UGMA/UTMA": 1,
    "Traditional IRA": 1,
    "Roth IRA (Custodial)": 2,
    "Trump Account": 2,
  },
  "Estate exclusion": {
    "Taxable Brokerage": 1,
    "Hold Until Death": 1,
    "529 Plan": 5,
    "UGMA/UTMA": 4,
    "Traditional IRA": 4,
    "Roth IRA (Custodial)": 5,
    "Trump Account": 5,
  },
};

const PALETTE = ["#2563eb", "#16a34a", "#d97706", "#7c3aed", "#dc2626", "#0891b2", "#db2777"];

interface Props {
  data: CompareResultDto;
}

export function TradeoffMatrix({ data }: Props) {
  const available = data.results.filter((r) => r.is_available);
  const rows = Object.keys(ATTRIBUTES).map((attr) => {
    const row: Record<string, number | string> = { attribute: attr };
    for (const r of available) {
      row[r.strategy_name] = ATTRIBUTES[attr][r.strategy_name] ?? 0;
    }
    return row;
  });

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <h3 className="font-semibold text-ink mb-2">Tradeoff matrix</h3>
      <p className="text-xs text-muted mb-3">
        Qualitative ratings on control, tax efficiency, flexibility, recipient access age, and
        estate-exclusion treatment. Higher = better.
      </p>
      <ResponsiveContainer width="100%" height={320}>
        <RadarChart data={rows}>
          <PolarGrid stroke="#e2e8f0" />
          <PolarAngleAxis dataKey="attribute" fontSize={11} stroke="#64748b" />
          <PolarRadiusAxis angle={30} domain={[0, 5]} fontSize={10} stroke="#94a3b8" />
          {available.map((r, i) => (
            <Radar
              key={r.strategy_name}
              dataKey={r.strategy_name}
              stroke={PALETTE[i % PALETTE.length]}
              fill={PALETTE[i % PALETTE.length]}
              fillOpacity={0.08}
            />
          ))}
          <Legend wrapperStyle={{ fontSize: 11 }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
