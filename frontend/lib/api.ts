import type { CompareResultDto, DonorInputsPayload } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function compareStrategies(
  payload: DonorInputsPayload
): Promise<CompareResultDto> {
  const res = await fetch(`${API_BASE}/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`Compare failed (${res.status}): ${detail}`);
  }
  return res.json();
}

export function pdfUrl(): string {
  return `${API_BASE}/pdf`;
}

export async function downloadPdf(payload: DonorInputsPayload): Promise<Blob> {
  const res = await fetch(pdfUrl(), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("PDF generation failed");
  return res.blob();
}

export async function fetchRulesVersion(): Promise<{
  tax_year: number;
  last_updated: string;
  source: string;
  bluej_enabled: boolean;
  aiwyn_validator_enabled: boolean;
}> {
  const res = await fetch(`${API_BASE}/rules/version`);
  return res.json();
}

export function formatMoney(value: string | number): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!isFinite(n)) return "—";
  return n.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}

/**
 * Compact USD denomination — $19K, $1.2M, $1.5B — when the magnitude is large
 * enough to make full-precision noise distracting. Used in chart axes and tight
 * spaces. Use `formatMoney` for tabular cells where the exact figure matters.
 */
export function formatMoneyCompact(value: string | number): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!isFinite(n)) return "—";
  const abs = Math.abs(n);
  const sign = n < 0 ? "-" : "";
  if (abs >= 1_000_000_000) return `${sign}$${(abs / 1_000_000_000).toFixed(2)}B`;
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(2)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(1)}K`;
  return `${sign}$${abs.toFixed(0)}`;
}

export function formatPercent(value: string | number, digits = 1): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!isFinite(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}

/**
 * Parse a user-entered string like "$19,000" or "19000" into a clean numeric
 * string the engine will accept. Returns "" if no digits are present.
 */
export function parseCurrencyInput(raw: string): string {
  const cleaned = raw.replace(/[^0-9.\-]/g, "");
  return cleaned;
}

/**
 * Format a numeric string as `$1,234` while the user is typing — preserves a
 * trailing decimal so partial input is editable.
 */
export function displayCurrencyInput(raw: string): string {
  if (raw === "" || raw == null) return "";
  const cleaned = parseCurrencyInput(raw);
  if (cleaned === "" || cleaned === "-") return cleaned;
  const n = parseFloat(cleaned);
  if (!isFinite(n)) return raw;
  const hasDecimal = cleaned.includes(".");
  const [int, dec] = cleaned.split(".");
  const intFmt = parseInt(int, 10).toLocaleString("en-US");
  return hasDecimal ? `$${intFmt}.${dec ?? ""}` : `$${intFmt}`;
}
