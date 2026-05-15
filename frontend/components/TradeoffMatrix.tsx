"use client";
import { useMemo, useState } from "react";
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
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

const ACCENT = "#4f46e5"; // indigo 600 — reserved for top performer
const PALETTE = [
  "#0ea5e9", // sky 500
  "#10b981", // emerald 500
  "#f59e0b", // amber 500
  "#8b5cf6", // violet 500
  "#06b6d4", // cyan 500
  "#ec4899", // pink 500
  "#64748b", // slate 500
];

const DEFAULT_VISIBLE = 3;

interface Props {
  data: CompareResultDto;
}

export function TradeoffMatrix({ data }: Props) {
  const available = data.results.filter((r) => r.is_available);

  // Rank by after-tax wealth — same ordering as ComparisonTable so the
  // "top performer" semantic is consistent across the dashboard.
  const ranked = useMemo(
    () =>
      [...available].sort(
        (a, b) =>
          parseFloat(b.after_tax_wealth_to_recipient) -
          parseFloat(a.after_tax_wealth_to_recipient)
      ),
    [available]
  );

  const winner = ranked[0]?.strategy_name;

  const colorByStrategy = useMemo(() => {
    const map: Record<string, string> = {};
    let i = 0;
    for (const r of ranked) {
      if (r.strategy_name === winner) {
        map[r.strategy_name] = ACCENT;
      } else {
        map[r.strategy_name] = PALETTE[i % PALETTE.length];
        i++;
      }
    }
    return map;
  }, [ranked, winner]);

  // Default to top-3 to avoid the seven-overlapping-polygons mess. User can
  // add or remove via chip toggles.
  const [visible, setVisible] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(
      ranked.map((r, i) => [r.strategy_name, i < DEFAULT_VISIBLE])
    )
  );

  const rows = Object.keys(ATTRIBUTES).map((attr) => {
    const row: Record<string, number | string> = { attribute: attr };
    for (const r of ranked) {
      row[r.strategy_name] = ATTRIBUTES[attr][r.strategy_name] ?? 0;
    }
    return row;
  });

  const visibleStrategies = ranked.filter((r) => visible[r.strategy_name]);

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-2 gap-3 flex-wrap">
        <div>
          <h3 className="font-semibold text-ink">Tradeoff matrix</h3>
          <p className="text-xs text-muted mt-0.5 max-w-prose">
            Qualitative ratings on five dimensions, normalized to a 0–5 scale (higher = better).
            Top three by after-tax wealth shown by default — toggle any strategy to compare.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 text-xs mb-3">
        {ranked.map((r, idx) => {
          const color = colorByStrategy[r.strategy_name];
          const isOn = visible[r.strategy_name];
          const isWinner = r.strategy_name === winner;
          return (
            <button
              key={r.strategy_name}
              onClick={() =>
                setVisible((v) => ({ ...v, [r.strategy_name]: !v[r.strategy_name] }))
              }
              className={`px-2 py-1 rounded-md border transition-colors ${
                isOn
                  ? isWinner
                    ? "bg-accent-soft border-accent-ring text-accent-hover font-medium"
                    : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                  : "bg-white border-slate-200 text-slate-400 hover:text-slate-600"
              }`}
              style={{
                borderLeftWidth: 3,
                borderLeftColor: isOn ? color : "#cbd5e1",
              }}
            >
              <span className="text-slate-400 mr-1 tabular-nums">#{idx + 1}</span>
              {r.strategy_name}
              {isWinner && isOn && <span className="ml-1 text-[10px]">★</span>}
            </button>
          );
        })}
      </div>

      {visibleStrategies.length === 0 ? (
        <div className="text-center text-sm text-muted py-12">
          Toggle a strategy above to plot its profile.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={320}>
          <RadarChart data={rows} outerRadius="75%">
            <PolarGrid stroke="#e2e8f0" />
            <PolarAngleAxis dataKey="attribute" fontSize={11} stroke="#475569" />
            <PolarRadiusAxis
              angle={30}
              domain={[0, 5]}
              fontSize={9}
              stroke="#94a3b8"
              tickCount={6}
            />
            {visibleStrategies.map((r) => {
              const isWinner = r.strategy_name === winner;
              return (
                <Radar
                  key={r.strategy_name}
                  name={r.strategy_name}
                  dataKey={r.strategy_name}
                  stroke={colorByStrategy[r.strategy_name]}
                  strokeWidth={isWinner ? 2.5 : 1.5}
                  fill={colorByStrategy[r.strategy_name]}
                  fillOpacity={isWinner ? 0.22 : 0.12}
                  isAnimationActive={false}
                />
              );
            })}
          </RadarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
