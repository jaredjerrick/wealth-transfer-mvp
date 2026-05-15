"use client";
import type {
  CompareResultDto,
  RecommendationDto,
  RecommendationCategory,
  RecommendationPriority,
} from "../lib/types";

interface Props {
  data: CompareResultDto;
}

interface WarningCard {
  message: string;
  strategy: string;
}

// Category → tint colors. Indigo is reserved for the page's primary accent,
// so we use it for estate (highest stakes); other categories get muted,
// trustworthy tints. Adding a new category requires a row here.
const CATEGORY_STYLE: Record<
  RecommendationCategory,
  { border: string; chip: string }
> = {
  Estate: { border: "#4f46e5", chip: "text-accent-hover" }, // indigo 600
  Education: { border: "#0ea5e9", chip: "text-sky-700" }, // sky 500
  "Family event": { border: "#8b5cf6", chip: "text-violet-700" }, // violet 500
  Custodial: { border: "#0891b2", chip: "text-cyan-700" }, // cyan 600
  Retirement: { border: "#10b981", chip: "text-emerald-700" }, // emerald 500
  "Step-up": { border: "#14b8a6", chip: "text-teal-700" }, // teal 500
  GST: { border: "#ec4899", chip: "text-pink-700" }, // pink 500
  Gifting: { border: "#f59e0b", chip: "text-amber-700" }, // amber 500
  Planning: { border: "#64748b", chip: "text-slate-600" }, // slate 500
};

export function RecommendationsPanel({ data }: Props) {
  const recs = data.recommendations; // already priority-sorted by the server

  const warningCards: WarningCard[] = data.results.flatMap((r) =>
    r.warnings.map((message) => ({ message, strategy: r.strategy_name }))
  );

  if (recs.length === 0 && warningCards.length === 0) return null;

  const highCount = recs.filter((r) => r.priority === "high").length;

  return (
    <div className="space-y-4">
      {recs.length > 0 && (
        <section>
          <header className="flex items-baseline justify-between mb-2">
            <div className="flex items-baseline gap-2">
              <h3 className="font-semibold text-ink">Recommendations</h3>
              {highCount > 0 && (
                <span className="text-[10px] uppercase tracking-wide font-semibold text-red-700 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded">
                  {highCount} high priority
                </span>
              )}
            </div>
            <span className="text-xs text-muted tabular-nums">
              {recs.length} {recs.length === 1 ? "item" : "items"}
            </span>
          </header>
          <div className="grid gap-3 sm:grid-cols-2">
            {recs.map((rec, i) => (
              <RecommendationCard key={i} rec={rec} />
            ))}
          </div>
        </section>
      )}

      {warningCards.length > 0 && (
        <section>
          <header className="flex items-baseline justify-between mb-2">
            <h3 className="font-semibold text-ink">Warnings</h3>
            <span className="text-xs text-muted tabular-nums">
              {warningCards.length} {warningCards.length === 1 ? "item" : "items"}
            </span>
          </header>
          <div className="grid gap-3 sm:grid-cols-2">
            {warningCards.map((w, i) => (
              <WarningCardEl key={i} w={w} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function RecommendationCard({ rec }: { rec: RecommendationDto }) {
  const style = CATEGORY_STYLE[rec.category] ?? CATEGORY_STYLE.Planning;
  const isHigh = rec.priority === "high";
  return (
    <article
      className="relative bg-white border border-slate-200 rounded-lg p-3.5 shadow-sm transition-shadow hover:shadow-md"
      style={{ borderLeftWidth: 4, borderLeftColor: style.border }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <Icon priority={rec.priority} />
        <span className={`text-[10px] uppercase tracking-wide font-medium ${style.chip}`}>
          {rec.category}
        </span>
        {isHigh && <PriorityBadge />}
      </div>
      <p className="text-sm text-slate-700 leading-snug">{rec.message}</p>
    </article>
  );
}

function WarningCardEl({ w }: { w: WarningCard }) {
  return (
    <article
      className="relative bg-white border border-amber-200 rounded-lg p-3.5 shadow-sm transition-shadow hover:shadow-md"
      style={{ borderLeftWidth: 4, borderLeftColor: "#f59e0b" }}
    >
      <div className="flex items-center gap-2 mb-1.5">
        <WarningIcon />
        <span className="text-[10px] uppercase tracking-wide font-medium text-amber-700">
          Warning
        </span>
        <span className="text-[10px] uppercase tracking-wide text-muted ml-auto">
          {w.strategy}
        </span>
      </div>
      <p className="text-sm text-slate-700 leading-snug">{w.message}</p>
    </article>
  );
}

function PriorityBadge() {
  return (
    <span className="ml-auto text-[10px] uppercase tracking-wide font-semibold text-red-700 bg-red-50 border border-red-200 px-1.5 py-0.5 rounded">
      High
    </span>
  );
}

function Icon({ priority }: { priority: RecommendationPriority }) {
  // High-priority recommendations get an alert icon; lower priorities get the
  // neutral info icon. Keeps the visual hierarchy honest.
  if (priority === "high") {
    return (
      <svg
        viewBox="0 0 20 20"
        fill="currentColor"
        className="w-4 h-4 text-red-600"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d="M8.485 2.495a1.75 1.75 0 013.03 0l6.28 10.875A1.75 1.75 0 0116.28 16H3.72a1.75 1.75 0 01-1.515-2.63l6.28-10.875zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 8a1 1 0 100-2 1 1 0 000 2z"
          clipRule="evenodd"
        />
      </svg>
    );
  }
  return (
    <svg
      viewBox="0 0 20 20"
      fill="currentColor"
      className="w-4 h-4 text-accent"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M10 2a8 8 0 100 16 8 8 0 000-16zm.75 5a.75.75 0 00-1.5 0v3.546L7.22 12.575a.75.75 0 101.06 1.06l2.47-2.469A.75.75 0 0011 10.5V7z"
        clipRule="evenodd"
      />
    </svg>
  );
}

function WarningIcon() {
  return (
    <svg
      viewBox="0 0 20 20"
      fill="currentColor"
      className="w-4 h-4 text-amber-500"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M8.485 2.495a1.75 1.75 0 013.03 0l6.28 10.875A1.75 1.75 0 0116.28 16H3.72a1.75 1.75 0 01-1.515-2.63l6.28-10.875zM10 6a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 6zm0 8a1 1 0 100-2 1 1 0 000 2z"
        clipRule="evenodd"
      />
    </svg>
  );
}
