import type { Metadata } from "next";
import { Header } from "@/components/Header";
import { ThemeProvider } from "@/components/ThemeProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Scout — AI Job Discovery",
  description:
    "Search, scrape, and AI-rank the best job opportunities with Scout.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <div className="relative min-h-screen">
            <div
              aria-hidden
              className="pointer-events-none absolute inset-0 bg-hero-grid bg-[size:48px_48px] opacity-40"
            />
            <Header />
            <main className="relative z-10">{children}</main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
