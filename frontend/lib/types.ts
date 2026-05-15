// Mirrors the engine's wire format from CompareResult.to_dict().

export type FilingStatus = "single" | "mfj" | "mfs" | "hoh";
export type StateCode = "NY" | "IL" | "TX";
export type MortalityModel = "deterministic" | "actuarial";

// Canonical vehicle keys — must match engine.inputs.VehicleKey on the backend.
export type VehicleKey =
  | "taxable_brokerage"
  | "hold_until_death"
  | "section_529"
  | "ugma_utma"
  | "traditional_ira"
  | "roth_ira"
  | "trump_account";

export interface AllocationItem {
  vehicle: VehicleKey;
  annual_amount: string;
}

export interface DonorInputsPayload {
  donor_age: number;
  donor_gross_income_agi: string;
  filing_status: FilingStatus;
  state: StateCode;
  nyc_resident?: boolean;
  donor_net_worth: string;
  spouse_present: boolean;
  num_children?: number;
  planned_retirement_age?: number | null;
  child_age: number;
  child_earned_income: string;
  child_expects_college?: boolean;
  existing_balances?: Partial<Record<VehicleKey, string>>;
  investment_horizon_years: number;
  annual_contribution: string;
  allocation?: AllocationItem[] | null;
  expected_pretax_return: string;
  inflation_rate?: string;
  mortality_model?: MortalityModel;
  tax_year?: number;
  elect_529_five_year?: boolean;
  elect_gift_splitting?: boolean;
  charitable_bequest_pct?: string;
  // GST / skip-generation
  elect_skip_generation?: boolean;
  // Life events
  plan_pay_college?: boolean;
  plan_pay_wedding?: boolean;
  plan_pay_first_home?: boolean;
  est_college_cost_today?: string;
  est_wedding_cost_today?: string;
  est_first_home_help_today?: string;
}

export interface TaxExplanation {
  line: string;
  label: string;
  amount: string;
  rationale: string;
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
  tax_explanations?: TaxExplanation[];
}

// Mirror of the backend `Recommendation` dataclass. `category` is one of the
// values listed in engine.py (Estate, Education, Family event, Custodial,
// Retirement, Step-up, GST, Gifting, Planning). `priority` is "high" | "normal"
// | "low" — set server-side based on dollar impact of the issue.
export type RecommendationCategory =
  | "Estate"
  | "Education"
  | "Family event"
  | "Custodial"
  | "Retirement"
  | "Step-up"
  | "GST"
  | "Gifting"
  | "Planning";

export type RecommendationPriority = "high" | "normal" | "low";

export interface RecommendationDto {
  message: string;
  category: RecommendationCategory;
  priority: RecommendationPriority;
}

export interface CompareResultDto {
  inputs: Record<string, unknown>;
  rules_version: { tax_year: number; last_updated: string; source: string };
  results: StrategyResultDto[];
  recommendations: RecommendationDto[];
}
