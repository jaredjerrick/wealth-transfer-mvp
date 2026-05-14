"use client";
import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { CompareResultDto } from "../lib/types";
import { formatMoney, formatMoneyCompact } from "../lib/api";

const PALETTE = [
  "#2563eb", "#16a34a", "#d97706", "#7c3aed", "#dc2626", "#0891b2", "#db2777",
];

interface Props {
  data: CompareResultDto;
}

export function AccumulationChart({ data }: Props) {
  const available = useMemo(() => data.results.filter((r) => r.is_available), [data]);
  const [visible, setVisible] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(available.map((r) => [r.strategy_name, true]))
  );

  const horizon = Math.max(...available.map((r) => r.year_by_year_projection.length));
  const series = useMemo(() => {
    const rows: Record<string, number | string>[] = [];
    for (let y = 0; y < horizon; y++) {
      const row: Record<string, number | string> = { year: y };
      for (const r of available) {
        const point = r.year_by_year_projection[y];
        if (point) row[r.strategy_name] = parseFloat(point.pretax_balance);
      }
      rows.push(row);
    }
    return rows;
  }, [available, horizon]);

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-ink">Accumulation by strategy</h3>
        <div className="flex flex-wrap gap-2 text-xs">
          {available.map((r, i) => (
            <button
              key={r.strategy_name}
              onClick={() => setVisible((v) => ({ ...v, [r.strategy_name]: !v[r.strategy_name] }))}
              className={`px-2 py-1 rounded border ${
                visible[r.strategy_name] ? "bg-slate-100 border-slate-300" : "bg-white border-slate-200 text-slate-400"
              }`}
              style={{ borderLeft: `4px solid ${PALETTE[i % PALETTE.length]}` }}
            >
              {r.strategy_name}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={series} margin={{ top: 5, right: 16, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="year" stroke="#64748b" fontSize={11} label={{ value: "Year", position: "insideBottom", offset: -3, fill: "#64748b", fontSize: 11 }} />
          <YAxis stroke="#64748b" fontSize={11} tickFormatter={(v) => formatMoneyCompact(v)} />
          <Tooltip formatter={(v: number) => formatMoney(v)} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          {available.map((r, i) =>
            visible[r.strategy_name] ? (
              <Line
                key={r.strategy_name}
                type="monotone"
                dataKey={r.strategy_name}
                stroke={PALETTE[i % PALETTE.length]}
                dot={false}
                strokeWidth={2}
              />
            ) : null
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
