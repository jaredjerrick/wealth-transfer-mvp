"use client";
import type { CompareResultDto, StrategyResultDto } from "../lib/types";
import { formatMoney, formatPercent } from "../lib/api";
import { CitationFootnote } from "./CitationFootnote";

interface Props {
  data: CompareResultDto;
}

export function ComparisonTable({ data }: Props) {
  const available = data.results.filter((r) => r.is_available);
  const blocked = data.results.filter((r) => !r.is_available);
  const sorted = [...available].sort(
    (a, b) =>
      parseFloat(b.after_tax_wealth_to_recipient) -
      parseFloat(a.after_tax_wealth_to_recipient)
  );
  const top = sorted.slice(0, Math.min(3, sorted.length));
  const winnerAfterTax = top[0]
    ? parseFloat(top[0].after_tax_wealth_to_recipient)
    : 0;

  return (
    <div className="space-y-4">
      {/* Top-N strategy summary cards — glance view */}
      {top.length > 0 && (
        <section>
          <div className="flex items-baseline justify-between mb-2">
            <h3 className="font-semibold text-ink">Top strategies</h3>
            <span className="text-xs text-muted">By after-tax wealth to heir</span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {top.map((r, i) => (
              <StrategyCard
                key={r.strategy_name}
                r={r}
                rank={i + 1}
                winnerAfterTax={winnerAfterTax}
              />
            ))}
          </div>
        </section>
      )}

      {/* Full numeric comparison — kept as a table because tables remain the
          best tool for scannable side-by-side numbers across many rows. On
          mobile (<sm), wrap in a <details> so phone users don't drown in a
          6-column table; the top-3 cards above already cover the essentials. */}
      <details open className="bg-white border border-slate-200 rounded-lg overflow-hidden group">
        <summary className="px-4 py-3 border-b border-slate-200 cursor-pointer list-none flex items-center justify-between hover:bg-slate-50">
          <div>
            <h3 className="font-semibold text-ink">Strategy comparison (full detail)</h3>
            <p className="text-xs text-muted mt-1">
              All strategies, sorted by after-tax wealth. Click § for the controlling authority.
            </p>
          </div>
          <span className="text-xs text-muted shrink-0 ml-3 group-open:rotate-180 transition-transform" aria-hidden="true">
            ▼
          </span>
        </summary>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-muted">
              <tr>
                <th className="text-left px-3 sm:px-4 py-2">Strategy</th>
                <th className="text-right px-3 sm:px-4 py-2 hidden sm:table-cell">Contributions</th>
                <th className="text-right px-3 sm:px-4 py-2 hidden md:table-cell">Pretax terminal</th>
                <th className="text-right px-3 sm:px-4 py-2 hidden md:table-cell">Total tax</th>
                <th className="text-right px-3 sm:px-4 py-2">After-tax to heir</th>
                <th className="text-right px-3 sm:px-4 py-2">ETR</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((r, i) => (
                <StrategyRow key={r.strategy_name} r={r} highlight={i === 0} />
              ))}
            </tbody>
          </table>
        </div>
      </details>

      {/* Unavailable strategies as cards instead of a bullet list. */}
      {blocked.length > 0 && (
        <section>
          <div className="flex items-baseline justify-between mb-2">
            <h3 className="font-semibold text-ink">Unavailable strategies</h3>
            <span className="text-xs text-muted tabular-nums">
              {blocked.length} {blocked.length === 1 ? "strategy" : "strategies"}
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {blocked.map((b) => (
              <BlockedCard key={b.strategy_name} r={b} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function StrategyCard({
  r,
  rank,
  winnerAfterTax,
}: {
  r: StrategyResultDto;
  rank: number;
  winnerAfterTax: number;
}) {
  const afterTax = parseFloat(r.after_tax_wealth_to_recipient);
  const pretax = parseFloat(r.pretax_terminal_value);
  const totalTax = pretax - afterTax;
  const isWinner = rank === 1;
  // How much less than the winner — useful for #2/#3 cards.
  const gapToWinner = winnerAfterTax - afterTax;
  const gapPct = winnerAfterTax > 0 ? (gapToWinner / winnerAfterTax) * 100 : 0;

  return (
    <article
      className={`relative bg-white border rounded-lg p-4 shadow-sm transition-shadow hover:shadow-md ${
        isWinner ? "border-accent-ring" : "border-slate-200"
      }`}
      style={
        isWinner
          ? { borderLeftWidth: 4, borderLeftColor: "#4f46e5" }
          : { borderLeftWidth: 4, borderLeftColor: "#cbd5e1" }
      }
    >
      <div className="flex items-center gap-2 mb-1.5">
        <span
          className={`text-[10px] font-semibold tabular-nums ${
            isWinner ? "text-accent-hover" : "text-muted"
          }`}
        >
          #{rank}
        </span>
        {isWinner && (
          <span className="text-[10px] uppercase tracking-wide font-semibold text-accent-hover">
            Top after-tax
          </span>
        )}
        <span className="ml-auto text-xs text-muted tabular-nums">
          ETR {formatPercent(r.effective_tax_rate)}
        </span>
      </div>
      <div className="text-sm font-semibold text-ink mb-2">
        {r.strategy_name}
        <CitationFootnote citations={r.citations} />
      </div>
      <div className="text-xs text-muted">After-tax to heir</div>
      <div
        className={`text-xl font-semibold tabular-nums ${
          isWinner ? "text-accent-hover" : "text-ink"
        }`}
      >
        {formatMoney(r.after_tax_wealth_to_recipient)}
      </div>
      <div className="mt-2 pt-2 border-t border-slate-100 grid grid-cols-2 gap-y-1 text-xs">
        <span className="text-muted">Pretax terminal</span>
        <span className="text-right tabular-nums text-slate-700">
          {formatMoney(r.pretax_terminal_value)}
        </span>
        <span className="text-muted">Total tax</span>
        <span className="text-right tabular-nums text-slate-700">{formatMoney(totalTax)}</span>
        {!isWinner && gapToWinner > 0 && (
          <>
            <span className="text-muted">Behind #1</span>
            <span className="text-right tabular-nums text-slate-700">
              −{formatMoney(gapToWinner)} ({gapPct.toFixed(1)}%)
            </span>
          </>
        )}
      </div>
    </article>
  );
}

function BlockedCard({ r }: { r: StrategyResultDto }) {
  return (
    <article
      className="relative bg-white border border-amber-200 rounded-lg p-3.5 shadow-sm"
      style={{ borderLeftWidth: 4, borderLeftColor: "#f59e0b" }}
    >
      <div className="flex items-center gap-2 mb-1">
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          className="w-4 h-4 text-amber-500"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M10 2a8 8 0 100 16 8 8 0 000-16zM6.28 6.28a.75.75 0 011.06 0L10 8.94l2.66-2.66a.75.75 0 111.06 1.06L11.06 10l2.66 2.66a.75.75 0 11-1.06 1.06L10 11.06l-2.66 2.66a.75.75 0 11-1.06-1.06L8.94 10 6.28 7.34a.75.75 0 010-1.06z"
            clipRule="evenodd"
          />
        </svg>
        <span className="text-[10px] uppercase tracking-wide font-semibold text-amber-700">
          Unavailable
        </span>
      </div>
      <div className="text-sm font-semibold text-ink mb-1">{r.strategy_name}</div>
      <p className="text-xs text-slate-700 leading-snug">{r.unavailable_reason}</p>
    </article>
  );
}

function StrategyRow({ r, highlight }: { r: StrategyResultDto; highlight: boolean }) {
  const totalTax = Object.values(r.taxes_paid_breakdown).reduce(
    (s, v) => s + parseFloat(v),
    0
  );
  return (
    <tr className={highlight ? "bg-accent-soft/40" : "border-t border-slate-100"}>
      <td className="px-3 sm:px-4 py-2 font-medium">
        {r.strategy_name}
        <CitationFootnote citations={r.citations} />
      </td>
      <td className="text-right px-3 sm:px-4 py-2 tabular-nums hidden sm:table-cell">
        {formatMoney(r.contribution_total)}
      </td>
      <td className="text-right px-3 sm:px-4 py-2 tabular-nums hidden md:table-cell">
        {formatMoney(r.pretax_terminal_value)}
      </td>
      <td className="text-right px-3 sm:px-4 py-2 tabular-nums hidden md:table-cell">
        {formatMoney(totalTax)}
      </td>
      <td
        className={`text-right px-3 sm:px-4 py-2 tabular-nums font-semibold ${
          highlight ? "text-accent-hover" : ""
        }`}
      >
        {formatMoney(r.after_tax_wealth_to_recipient)}
      </td>
      <td className="text-right px-3 sm:px-4 py-2 tabular-nums">{formatPercent(r.effective_tax_rate)}</td>
    </tr>
  );
}
