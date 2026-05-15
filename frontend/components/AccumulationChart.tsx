"use client";
import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type { CompareResultDto } from "../lib/types";
import { formatMoney, formatMoneyCompact } from "../lib/api";

// Muted, trustworthy series palette. The accent (indigo) is reserved for the
// strategy with the best after-tax outcome — it should pop.
const ACCENT = "#4f46e5";
const PALETTE = [
  "#0ea5e9", // sky 500
  "#10b981", // emerald 500
  "#f59e0b", // amber 500
  "#8b5cf6", // violet 500
  "#06b6d4", // cyan 500
  "#ec4899", // pink 500
  "#64748b", // slate 500
];

interface Props {
  data: CompareResultDto;
}

export function AccumulationChart({ data }: Props) {
  const available = useMemo(() => data.results.filter((r) => r.is_available), [data]);

  // The "winner" — top strategy by after-tax wealth — gets the indigo accent.
  const winner = useMemo(() => {
    return [...available].sort(
      (a, b) =>
        parseFloat(b.after_tax_wealth_to_recipient) -
        parseFloat(a.after_tax_wealth_to_recipient)
    )[0]?.strategy_name;
  }, [available]);

  // Assign a stable color per strategy: indigo for the winner, palette rotation
  // for the rest in their original ordering.
  const colorByStrategy = useMemo(() => {
    const map: Record<string, string> = {};
    let i = 0;
    for (const r of available) {
      if (r.strategy_name === winner) {
        map[r.strategy_name] = ACCENT;
      } else {
        map[r.strategy_name] = PALETTE[i % PALETTE.length];
        i++;
      }
    }
    return map;
  }, [available, winner]);

  const [visible, setVisible] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(available.map((r) => [r.strategy_name, true]))
  );
  const [focused, setFocused] = useState<string | null>(null);

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

  const allOn = available.every((r) => visible[r.strategy_name]);
  const allOff = available.every((r) => !visible[r.strategy_name]);

  function toggleAll(on: boolean) {
    setVisible(Object.fromEntries(available.map((r) => [r.strategy_name, on])));
  }

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-3 gap-3 flex-wrap">
        <div>
          <h3 className="font-semibold text-ink">Accumulation by strategy</h3>
          <p className="text-xs text-muted mt-0.5">
            Hover a chip to focus one line. Click to toggle.
          </p>
        </div>
        <div className="flex gap-2 text-xs">
          <button
            onClick={() => toggleAll(true)}
            disabled={allOn}
            className="px-2 py-1 rounded border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Show all
          </button>
          <button
            onClick={() => toggleAll(false)}
            disabled={allOff}
            className="px-2 py-1 rounded border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Hide all
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 text-xs mb-3">
        {available.map((r) => {
          const color = colorByStrategy[r.strategy_name];
          const isOn = visible[r.strategy_name];
          const isWinner = r.strategy_name === winner;
          return (
            <button
              key={r.strategy_name}
              onClick={() =>
                setVisible((v) => ({ ...v, [r.strategy_name]: !v[r.strategy_name] }))
              }
              onMouseEnter={() => isOn && setFocused(r.strategy_name)}
              onMouseLeave={() => setFocused(null)}
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
              {r.strategy_name}
              {isWinner && isOn && <span className="ml-1 text-[10px]">★</span>}
            </button>
          );
        })}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={series} margin={{ top: 5, right: 16, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="year"
            stroke="#64748b"
            fontSize={11}
            label={{
              value: "Year",
              position: "insideBottom",
              offset: -10,
              fill: "#64748b",
              fontSize: 11,
            }}
          />
          <YAxis
            stroke="#64748b"
            fontSize={11}
            tickFormatter={(v) => formatMoneyCompact(v)}
            width={60}
          />
          <Tooltip
            content={<TooltipContent visible={visible} colorByStrategy={colorByStrategy} />}
            cursor={{ stroke: "#94a3b8", strokeDasharray: "4 4" }}
          />
          {available.map((r) => {
            if (!visible[r.strategy_name]) return null;
            const isFocused = focused === r.strategy_name;
            const anyFocused = focused !== null;
            const dimmed = anyFocused && !isFocused;
            return (
              <Line
                key={r.strategy_name}
                type="monotone"
                dataKey={r.strategy_name}
                stroke={colorByStrategy[r.strategy_name]}
                strokeOpacity={dimmed ? 0.18 : 1}
                strokeWidth={isFocused ? 3 : r.strategy_name === winner ? 2.5 : 1.75}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
                isAnimationActive={false}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

interface TooltipPayloadEntry {
  dataKey: string;
  value: number;
  color: string;
}

function TooltipContent({
  active,
  payload,
  label,
  visible,
  colorByStrategy,
}: {
  active?: boolean;
  payload?: TooltipPayloadEntry[];
  label?: number;
  visible: Record<string, boolean>;
  colorByStrategy: Record<string, string>;
}) {
  if (!active || !payload || payload.length === 0) return null;

  // Sort by value desc and filter to only visible series.
  const rows = payload
    .filter((p) => visible[p.dataKey])
    .sort((a, b) => b.value - a.value);

  if (rows.length === 0) return null;

  return (
    <div className="bg-white border border-slate-200 rounded-md shadow-lg px-3 py-2 text-xs">
      <div className="font-medium text-ink mb-1.5">Year {label}</div>
      <div className="space-y-1">
        {rows.map((p) => (
          <div key={p.dataKey} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-slate-600">
              <span
                className="inline-block w-2 h-2 rounded-sm"
                style={{ backgroundColor: colorByStrategy[p.dataKey] ?? p.color }}
              />
              {p.dataKey}
            </span>
            <span className="font-medium text-ink tabular-nums">{formatMoney(p.value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
