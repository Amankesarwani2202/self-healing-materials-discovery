import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SelfHeal Materials | Research Discovery",
  description: "Evidence-led discovery and comparison of self-healing polymer materials from published research.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}