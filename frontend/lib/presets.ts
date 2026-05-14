// Named preset portfolios for the diversified-allocation feature. Each preset
// returns a list of {vehicle, weight} entries whose weights sum to 1.0. The
// InputForm multiplies the user's `annual_contribution` by each weight to
// produce the AllocationItem array sent to the engine.

import type { VehicleKey } from "./types";

export interface AllocationPreset {
  id: string;
  name: string;
  tagline: string;
  description: string;
  weights: Array<{ vehicle: VehicleKey; weight: number }>;
}

export const PRESETS: AllocationPreset[] = [
  {
    id: "custom",
    name: "Custom",
    tagline: "Edit every weight yourself.",
    description:
      "Start blank and assign whatever you like. Caps enforced per vehicle (Roth limited to earned income and the IRA limit; Trump Account limited to $5K/yr; etc.).",
    weights: [],
  },
  {
    id: "education_heavy",
    name: "Education-Heavy",
    tagline: "Maximize 529 + Roth runway.",
    description:
      "60% into a 529 for qualified-education-tax-free growth, 20% Roth IRA (assumes the child has earned income), and 20% UTMA for flexibility on non-education needs.",
    weights: [
      { vehicle: "section_529", weight: 0.6 },
      { vehicle: "roth_ira", weight: 0.2 },
      { vehicle: "ugma_utma", weight: 0.2 },
    ],
  },
  {
    id: "roth_forward",
    name: "Roth-Forward",
    tagline: "Pile into Roth, top up with 529 and Trump.",
    description:
      "Best when the child has earned income early. 70% Roth IRA (subject to earned-income / IRA-limit caps), 20% 529, 10% Trump Account.",
    weights: [
      { vehicle: "roth_ira", weight: 0.7 },
      { vehicle: "section_529", weight: 0.2 },
      { vehicle: "trump_account", weight: 0.1 },
    ],
  },
  {
    id: "estate_shield",
    name: "Estate Shield",
    tagline: "Move wealth out of the donor's estate quickly.",
    description:
      "Designed for donors near or above the §2010 / state estate-tax thresholds. 50% 529, 30% UTMA, 20% Roth IRA. All three vehicles remove the assets from the donor's gross estate (529 under §529(c)(4); UTMA via completed gift; Roth as a completed gift to the child's own account).",
    weights: [
      { vehicle: "section_529", weight: 0.5 },
      { vehicle: "ugma_utma", weight: 0.3 },
      { vehicle: "roth_ira", weight: 0.2 },
    ],
  },
  {
    id: "balanced",
    name: "Balanced",
    tagline: "Diversified across five vehicles.",
    description:
      "A bit of each: 30% 529, 20% Roth, 20% UTMA, 20% Hold-Until-Death (donor's brokerage), 10% Trump Account.",
    weights: [
      { vehicle: "section_529", weight: 0.3 },
      { vehicle: "roth_ira", weight: 0.2 },
      { vehicle: "ugma_utma", weight: 0.2 },
      { vehicle: "hold_until_death", weight: 0.2 },
      { vehicle: "trump_account", weight: 0.1 },
    ],
  },
  {
    id: "tax_deferred_max",
    name: "Tax-Deferred Max",
    tagline: "Maximize tax-deferred / tax-free wrappers.",
    description:
      "60% 529, 25% Roth IRA, 15% Trump Account. Skips Traditional IRA (poor for IRD-burdened heirs) and taxable accounts (full tax drag).",
    weights: [
      { vehicle: "section_529", weight: 0.6 },
      { vehicle: "roth_ira", weight: 0.25 },
      { vehicle: "trump_account", weight: 0.15 },
    ],
  },
];

export const DEFAULT_PRESET_ID = "balanced";
