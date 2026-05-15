import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}", "./components/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        muted: "#64748b",
        // Accent palette — Indigo 600 family. Use `accent` for CTAs and the
        // currently focused data series across charts. `accent-soft` is for
        // hover backgrounds and chip fills.
        accent: "#4f46e5",
        "accent-hover": "#4338ca",
        "accent-soft": "#eef2ff",
        "accent-ring": "#c7d2fe",
      },
    },
  },
  plugins: [],
};
export default config;
