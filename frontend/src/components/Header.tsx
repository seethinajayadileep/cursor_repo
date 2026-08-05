"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import { useTheme } from "./ThemeProvider";

const links = [
  { href: "/", label: "Discover" },
  { href: "/saved", label: "Saved" },
  { href: "/insights", label: "Insights" },
];

export function Header() {
  const pathname = usePathname();
  const { theme, toggle } = useTheme();

  return (
    <header className="relative z-20 border-b border-ink-800/40 bg-ink-950/70 backdrop-blur-md dark:border-white/10">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
        <Link href="/" className="group flex items-baseline gap-2">
          <span className="font-display text-2xl tracking-tight text-mist transition group-hover:text-signal sm:text-3xl">
            Scout
          </span>
          <span className="hidden text-xs uppercase tracking-[0.22em] text-ink-300 sm:inline">
            Job Discovery
          </span>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={clsx(
                "rounded-md px-3 py-1.5 text-sm transition",
                pathname === link.href
                  ? "bg-signal/15 text-signal"
                  : "text-ink-200 hover:bg-white/5 hover:text-mist"
              )}
            >
              {link.label}
            </Link>
          ))}
          <button
            type="button"
            onClick={toggle}
            aria-label="Toggle theme"
            className="ml-1 rounded-md border border-white/10 px-3 py-1.5 text-sm text-ink-200 transition hover:border-signal/40 hover:text-signal"
          >
            {theme === "dark" ? "Light" : "Dark"}
          </button>
        </nav>
      </div>
    </header>
  );
}
