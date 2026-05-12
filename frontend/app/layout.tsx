import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Wealth Transfer Strategy Comparison",
  description:
    "Compare federal and state tax outcomes across six wealth-transfer strategies. Educational model — not tax or legal advice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-slate-50 text-ink min-h-screen">{children}</body>
    </html>
  );
}
