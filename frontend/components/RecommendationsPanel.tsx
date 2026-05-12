"use client";
import type { CompareResultDto } from "../lib/types";

interface Props {
  data: CompareResultDto;
}

export function RecommendationsPanel({ data }: Props) {
  const warnings = data.results.flatMap((r) =>
    r.warnings.map((w) => ({ strategy: r.strategy_name, message: w }))
  );

  return (
    <div className="space-y-4">
      {data.recommendations.length > 0 && (
        <div className="bg-blue-50/60 border border-blue-200 rounded-lg p-4">
          <h3 className="font-semibold text-blue-900 mb-2">Recommendations</h3>
          <ul className="space-y-2 text-sm text-blue-900">
            {data.recommendations.map((rec, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-blue-500 mt-1">›</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {warnings.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <h3 className="font-semibold text-amber-900 mb-2">Warnings</h3>
          <ul className="space-y-2 text-sm text-amber-900">
            {warnings.map((w, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-amber-500 mt-1">⚠</span>
                <span>
                  <span className="font-medium">[{w.strategy}]</span> {w.message}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
