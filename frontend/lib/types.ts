// Mirrors the engine's wire format from CompareResult.to_dict().

export type FilingStatus = "single" | "mfj" | "mfs" | "hoh";
export type StateCode = "NY" | "IL" | "TX";
export type MortalityModel = "deterministic" | "actuarial";

export interface DonorInputsPayload {
  donor_age: number;
  donor_gross_income_agi: string;
  filing_status: FilingStatus;
  state: StateCode;
  nyc_resident?: boolean;
  donor_net_worth: string;
  spouse_present: boolean;
  child_age: number;
  child_earned_income: string;
  investment_horizon_years: number;
  annual_contribution: string;
  expected_pretax_return: string;
  inflation_rate?: string;
  mortality_model?: MortalityModel;
  tax_year?: number;
  elect_529_five_year?: boolean;
  elect_gift_splitting?: boolean;
  charitable_bequest_pct?: string;
}

export interface Citation {
  section: string;
  description: string;
  url: string | null;
  scope: string;
}

export interface YearlyRow {
  year_index: number;
  child_age: number;
  contributions_to_date: string;
  pretax_balance: string;
  annual_tax_drag: string;
  cumulative_tax_drag: string;
}

export interface StrategyResultDto {
  strategy_name: string;
  is_available: boolean;
  unavailable_reason: string | null;
  contribution_total: string;
  pretax_terminal_value: string;
  taxes_paid_breakdown: Record<string, string>;
  after_tax_wealth_to_recipient: string;
  effective_tax_rate: string;
  year_by_year_projection: YearlyRow[];
  citations: Citation[];
  assumptions: string[];
  warnings: string[];
}

export interface CompareResultDto {
  inputs: Record<string, unknown>;
  rules_version: { tax_year: number; last_updated: string; source: string };
  results: StrategyResultDto[];
  recommendations: string[];
}
