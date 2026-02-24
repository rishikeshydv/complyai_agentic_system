import type { Metadata } from "next";

import Header from "@/components/header/header";
import { onest } from "@/font/font";
import "./globals.css";

export const metadata: Metadata = {
  title: "Comply AI - Agentic Alert Copilot",
  description: "Evidence-grounded AML and sanctions case generation platform.",
  icons: {
    icon: "/logo/comply-icon.ico",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={onest.className}>
        <Header />
        {children}
      </body>
    </html>
  );
}
