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

export function formatPercent(value: string | number, digits = 1): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  if (!isFinite(n)) return "—";
  return `${(n * 100).toFixed(digits)}%`;
}
