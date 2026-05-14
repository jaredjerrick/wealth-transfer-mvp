"use client";
import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { CompareResultDto, StrategyResultDto } from "../lib/types";
import { formatMoney, formatMoneyCompact } from "../lib/api";

interface Props {
  data: CompareResultDto;
}

export function TaxDragWaterfall({ data }: Props) {
  const available = data.results.filter((r) => r.is_available);
  const [selected, setSelected] = useState(available[0]?.strategy_name || "");
  const strategy = available.find((r) => r.strategy_name === selected) || available[0];
  if (!strategy) return null;

  const pretax = parseFloat(strategy.pretax_terminal_value);
  const items = Object.entries(strategy.taxes_paid_breakdown).filter(
    ([, v]) => Math.abs(parseFloat(v)) > 0.01
  );
  const after = parseFloat(strategy.after_tax_wealth_to_recipient);

  const rows = [
    { label: "Pretax terminal", amount: pretax, kind: "start" },
    ...items.map(([k, v]) => ({
      label: prettify(k),
      amount: -parseFloat(v),
      kind: "drag",
    })),
    { label: "After-tax to heir", amount: after, kind: "end" },
  ];

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-ink">Tax drag waterfall</h3>
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
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={rows} margin={{ top: 5, right: 16, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="label" stroke="#64748b" fontSize={10} angle={-15} textAnchor="end" height={50} />
          <YAxis
            stroke="#64748b"
            fontSize={11}
            tickFormatter={(v) => formatMoneyCompact(v)}
          />
          <Tooltip formatter={(v: number) => formatMoney(v)} />
          <Bar dataKey="amount">
            {rows.map((r, i) => (
              <Cell
                key={i}
                fill={
                  r.kind === "start" || r.kind === "end" ? "#2563eb" : "#dc2626"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function prettify(key: string) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (m) => m.toUpperCase());
}
