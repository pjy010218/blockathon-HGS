import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tideproof · BC Water Record",
  description: "Compare, contribute, and preserve British Columbia water-quality records.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
