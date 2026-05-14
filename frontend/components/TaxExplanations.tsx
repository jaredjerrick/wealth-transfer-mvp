"use client";
import { useState } from "react";
import type { CompareResultDto, StrategyResultDto } from "../lib/types";
import { formatMoney } from "../lib/api";

interface Props {
  data: CompareResultDto;
}

export function TaxExplanations({ data }: Props) {
  const available = data.results.filter((r) => r.is_available && (r.tax_explanations?.length ?? 0) > 0);
  const [selected, setSelected] = useState<string>(available[0]?.strategy_name || "");
  const strategy: StrategyResultDto | undefined =
    available.find((r) => r.strategy_name === selected) || available[0];
  if (!strategy) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-ink">What taxes were paid &mdash; and why</h3>
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="text-sm rounded border border-slate-300 px-2 py-1 bg-white"
        >
          {available.map((r) => (
            <option key={r.strategy_name} value={r.strategy_name}>
              {r.strategy_name}
            </option>
          ))}
        </select>
      </div>
      <ul className="divide-y divide-slate-100">
        {(strategy.tax_explanations ?? []).map((ex, i) => {
          const amt = parseFloat(ex.amount);
          const isCredit = amt < 0;
          const isMeta = ex.line === "__composite__";
          return (
            <li key={i} className="py-2 flex gap-3">
              <div className="w-44 shrink-0">
                <div className="font-medium text-sm">{ex.label}</div>
                {!isMeta && (
                  <div className={`text-sm tabular-nums ${isCredit ? "text-emerald-700" : "text-red-700"}`}>
                    {isCredit ? "-" : ""}{formatMoney(Math.abs(amt))}
                    {isCredit && <span className="ml-1 text-xs text-muted">(saving)</span>}
                  </div>
                )}
              </div>
              <div className="text-sm text-ink/80 flex-1">{ex.rationale}</div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
