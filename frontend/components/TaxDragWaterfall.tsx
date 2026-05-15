"use client";
import { useState, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";
import type { CompareResultDto } from "../lib/types";
import { formatMoney, formatMoneyCompact } from "../lib/api";

const ACCENT = "#4f46e5"; // indigo 600 — pretax start + after-tax end
const DRAG = "#ef4444"; // red 500 — tax drag steps

interface Props {
  data: CompareResultDto;
}

interface WaterfallRow {
  label: string;
  base: number; // invisible "floor" — supports a floating bar
  value: number; // visible portion height
  display: number; // signed value for tooltip
  kind: "start" | "drag" | "end";
}

export function TaxDragWaterfall({ data }: Props) {
  const available = data.results.filter((r) => r.is_available);

  // Default to the top strategy by after-tax wealth so the chart opens to
  // the most useful view.
  const defaultStrategy = useMemo(() => {
    return [...available].sort(
      (a, b) =>
        parseFloat(b.after_tax_wealth_to_recipient) -
        parseFloat(a.after_tax_wealth_to_recipient)
    )[0]?.strategy_name;
  }, [available]);

  const [selected, setSelected] = useState<string>(defaultStrategy || "");
  const strategy =
    available.find((r) => r.strategy_name === selected) ||
    available.find((r) => r.strategy_name === defaultStrategy) ||
    available[0];

  const rows = useMemo<WaterfallRow[]>(() => {
    if (!strategy) return [];
    const pretax = parseFloat(strategy.pretax_terminal_value);
    const after = parseFloat(strategy.after_tax_wealth_to_recipient);
    const drags = Object.entries(strategy.taxes_paid_breakdown)
      .map(([k, v]) => [k, parseFloat(v)] as [string, number])
      .filter(([, v]) => Math.abs(v) > 0.01);

    // Build a true running waterfall: each drag step floats from
    // (running balance - drag) up to (running balance).
    const out: WaterfallRow[] = [];
    let running = pretax;

    out.push({
      label: "Pretax\nterminal",
      base: 0,
      value: pretax,
      display: pretax,
      kind: "start",
    });

    for (const [k, v] of drags) {
      const next = running - v;
      out.push({
        label: prettify(k),
        base: next,
        value: v,
        display: -v,
        kind: "drag",
      });
      running = next;
    }

    out.push({
      label: "After-tax\nto heir",
      base: 0,
      value: after,
      display: after,
      kind: "end",
    });

    return out;
  }, [strategy]);

  if (!strategy) return null;

  const totalDrag = parseFloat(strategy.pretax_terminal_value) - parseFloat(strategy.after_tax_wealth_to_recipient);
  const dragPct = parseFloat(strategy.pretax_terminal_value) > 0
    ? (totalDrag / parseFloat(strategy.pretax_terminal_value)) * 100
    : 0;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-3 gap-3 flex-wrap">
        <div>
          <h3 className="font-semibold text-ink">Tax drag waterfall</h3>
          <p className="text-xs text-muted mt-0.5">
            How taxes erode the pretax terminal balance, in order.
          </p>
        </div>
        <select
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
          className="text-sm rounded border border-slate-300 px-2 py-1 bg-white text-ink focus:outline-none focus:ring-2 focus:ring-accent-ring focus:border-accent"
        >
          {available.map((r) => (
            <option key={r.strategy_name} value={r.strategy_name}>
              {r.strategy_name}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3 text-center">
        <Headline
          label="Pretax terminal"
          value={formatMoneyCompact(parseFloat(strategy.pretax_terminal_value))}
          tone="accent"
        />
        <Headline
          label="Total tax drag"
          value={formatMoneyCompact(totalDrag)}
          sub={`${dragPct.toFixed(1)}%`}
          tone="drag"
        />
        <Headline
          label="After-tax to heir"
          value={formatMoneyCompact(parseFloat(strategy.after_tax_wealth_to_recipient))}
          tone="accent"
        />
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={rows} margin={{ top: 10, right: 16, left: 0, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="label"
            stroke="#64748b"
            fontSize={10}
            interval={0}
            tick={<MultilineTick />}
            height={36}
          />
          <YAxis
            stroke="#64748b"
            fontSize={11}
            tickFormatter={(v) => formatMoneyCompact(v)}
            width={60}
          />
          <Tooltip content={<TooltipContent />} cursor={{ fill: "#f1f5f9" }} />
          {/* Invisible "floor" bar to lift each step to its starting height */}
          <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />
          {/* Visible value bar */}
          <Bar dataKey="value" stackId="w" isAnimationActive={false}>
            {rows.map((r, i) => (
              <Cell
                key={i}
                fill={r.kind === "drag" ? DRAG : ACCENT}
                fillOpacity={r.kind === "drag" ? 0.85 : 1}
              />
            ))}
            <LabelList
              dataKey="display"
              position="top"
              content={<BarTopLabel />}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function Headline({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub?: string;
  tone: "accent" | "drag";
}) {
  const valueClass = tone === "accent" ? "text-accent-hover" : "text-red-600";
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-md py-2 px-2">
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <div className={`text-base font-semibold tabular-nums ${valueClass}`}>{value}</div>
      {sub && <div className="text-[11px] text-muted tabular-nums">{sub}</div>}
    </div>
  );
}

function MultilineTick(props: any) {
  const { x, y, payload } = props;
  const lines = String(payload.value).split("\n");
  return (
    <g transform={`translate(${x},${y + 6})`}>
      {lines.map((line, i) => (
        <text
          key={i}
          x={0}
          y={i * 12}
          textAnchor="middle"
          fontSize={10}
          fill="#64748b"
        >
          {line}
        </text>
      ))}
    </g>
  );
}

function BarTopLabel(props: any) {
  const { x, y, width, value } = props;
  if (value === undefined || value === null) return null;
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || Math.abs(numeric) < 1) return null;
  return (
    <text
      x={x + width / 2}
      y={y - 4}
      textAnchor="middle"
      fontSize={10}
      fill="#475569"
      className="tabular-nums"
    >
      {numeric < 0 ? "−" : ""}
      {formatMoneyCompact(Math.abs(numeric))}
    </text>
  );
}

function TooltipContent({ active, payload }: any) {
  if (!active || !payload || payload.length === 0) return null;
  const row: WaterfallRow | undefined = payload[0]?.payload;
  if (!row) return null;
  const dollarLabel =
    row.kind === "drag"
      ? `−${formatMoney(row.value)}`
      : formatMoney(row.value);
  const label = row.kind === "drag" ? "Tax drag" : row.kind === "start" ? "Starting value" : "Ending value";
  return (
    <div className="bg-white border border-slate-200 rounded-md shadow-lg px-3 py-2 text-xs">
      <div className="font-medium text-ink mb-0.5">{String(row.label).replace("\n", " ")}</div>
      <div className="flex justify-between gap-4">
        <span className="text-muted">{label}</span>
        <span
          className={`tabular-nums font-medium ${
            row.kind === "drag" ? "text-red-600" : "text-accent-hover"
          }`}
        >
          {dollarLabel}
        </span>
      </div>
    </div>
  );
}

function prettify(key: string) {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (m) => m.toUpperCase());
}
