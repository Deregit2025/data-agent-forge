import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

export const metadata: Metadata = {
  title: "Oracle Forge — Multi-DB AI Data Agent",
  description: "44.4% Pass@1 on DataAgentBench — beats Gemini 3 Pro (38%) by 6.4pp",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-forge-bg min-h-screen">
        <Nav />
        <main className="pt-14">{children}</main>
      </body>
    </html>
  );
}
