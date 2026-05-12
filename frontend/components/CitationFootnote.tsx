"use client";
import { useState } from "react";
import type { Citation } from "../lib/types";

interface Props {
  citations: Citation[];
  label?: string;
}

export function CitationFootnote({ citations, label = "§" }: Props) {
  const [open, setOpen] = useState(false);
  if (!citations || citations.length === 0) return null;

  return (
    <span className="relative inline-block ml-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        onBlur={() => setTimeout(() => setOpen(false), 200)}
        className="text-blue-700 text-xs underline decoration-dotted cursor-help align-super"
        aria-label="View citations"
      >
        {label}
      </button>
      {open && (
        <span className="citation-hover left-0 top-5 min-w-[18rem] block">
          <span className="font-semibold text-slate-800 block mb-1">
            Controlling authorities ({citations.length})
          </span>
          {citations.map((c, i) => (
            <span key={i} className="block py-1 border-b border-slate-100 last:border-0">
              <span className="font-medium text-slate-900">{c.section}</span>
              <span className="text-slate-600">— {c.description}</span>
              {c.url && (
                <a
                  href={c.url}
                  target="_blank"
                  rel="noreferrer"
                  className="block text-blue-600 hover:underline text-[10px] mt-0.5"
                >
                  {c.url}
                </a>
              )}
            </span>
          ))}
        </span>
      )}
    </span>
  );
}
