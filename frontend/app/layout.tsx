import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Water Audit Trail",
  description: "A source-preserving water quality provenance viewer",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
