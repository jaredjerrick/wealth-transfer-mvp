import "./globals.css";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "Wealth Transfer Strategy Comparison",
  description:
    "Compare federal and state tax outcomes across seven wealth-transfer strategies plus an optional Diversified Portfolio composite. Educational model — not tax or legal advice.",
};

// Explicit viewport — Next.js sets a default, but pinning width=device-width
// here makes it obvious this is a mobile-aware app. user-scalable left at
// default (allowed) for accessibility.
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-ink min-h-screen">{children}</body>
    </html>
  );
}
