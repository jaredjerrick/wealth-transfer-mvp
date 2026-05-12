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
    (a, b) => parseFloat(b.after_tax_wealth_to_recipient) - parseFloat(a.after_tax_wealth_to_recipient)
  );

  return (
    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200">
        <h3 className="font-semibold text-ink">Strategy comparison</h3>
        <p className="text-xs text-muted mt-1">
          Sorted by after-tax wealth to recipient. Every dollar traces to the cited authority — click the §.
        </p>
      </div>
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-xs uppercase text-muted">
          <tr>
            <th className="text-left px-4 py-2">Strategy</th>
            <th className="text-right px-4 py-2">Contributions</th>
            <th className="text-right px-4 py-2">Pretax terminal</th>
            <th className="text-right px-4 py-2">Total tax</th>
            <th className="text-right px-4 py-2">After-tax to heir</th>
            <th className="text-right px-4 py-2">ETR</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r, i) => (
            <StrategyRow key={r.strategy_name} r={r} highlight={i === 0} />
          ))}
        </tbody>
      </table>
      {blocked.length > 0 && (
        <div className="border-t border-slate-200 px-4 py-3 bg-amber-50 text-sm text-amber-900">
          <div className="font-medium mb-1">Unavailable strategies:</div>
          <ul className="list-disc list-inside space-y-1 text-xs">
            {blocked.map((b) => (
              <li key={b.strategy_name}>
                <span className="font-medium">{b.strategy_name}:</span> {b.unavailable_reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function StrategyRow({ r, highlight }: { r: StrategyResultDto; highlight: boolean }) {
  const totalTax = Object.values(r.taxes_paid_breakdown).reduce((s, v) => s + parseFloat(v), 0);
  return (
    <tr className={highlight ? "bg-emerald-50/40" : "border-t border-slate-100"}>
      <td className="px-4 py-2 font-medium">
        {r.strategy_name}
        <CitationFootnote citations={r.citations} />
      </td>
      <td className="text-right px-4 py-2 tabular-nums">{formatMoney(r.contribution_total)}</td>
      <td className="text-right px-4 py-2 tabular-nums">{formatMoney(r.pretax_terminal_value)}</td>
      <td className="text-right px-4 py-2 tabular-nums">{formatMoney(totalTax)}</td>
      <td className="text-right px-4 py-2 tabular-nums font-semibold">
        {formatMoney(r.after_tax_wealth_to_recipient)}
      </td>
      <td className="text-right px-4 py-2 tabular-nums">{formatPercent(r.effective_tax_rate)}</td>
    </tr>
  );
}
