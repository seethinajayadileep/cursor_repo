"use client";

import type { CompanyTrend, SalaryInsight } from "@/types";

interface Props {
  salary?: SalaryInsight | null;
  companies?: CompanyTrend[];
}

export function InsightsPanel({ salary, companies }: Props) {
  if (!salary && (!companies || companies.length === 0)) return null;

  return (
    <section className="animate-rise-delay space-y-6 border-t border-white/10 pt-8">
      <div>
        <h2 className="font-display text-2xl text-mist">Market pulse</h2>
        <p className="mt-1 text-sm text-ink-300">
          Salary bands and hiring signals from this search.
        </p>
      </div>

      {salary && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Median" value={fmt(salary.median, salary.currency)} />
          <Stat label="Average" value={fmt(salary.average, salary.currency)} />
          <Stat label="Low" value={fmt(salary.min, salary.currency)} />
          <Stat label="High" value={fmt(salary.max, salary.currency)} />
        </div>
      )}

      {companies && companies.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-xs uppercase tracking-[0.18em] text-ink-400">
            Company hiring trends
          </h3>
          <ul className="divide-y divide-white/10">
            {companies.slice(0, 6).map((c) => (
              <li
                key={c.company}
                className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm"
              >
                <div>
                  <p className="text-mist">{c.company}</p>
                  <p className="text-xs text-ink-400">
                    {c.topRoles.slice(0, 2).join(" · ")}
                  </p>
                </div>
                <div className="text-right text-ink-300">
                  <p>{c.openings} openings</p>
                  <p className="text-xs">
                    avg score {c.averageScore} · {c.remoteShare}% remote
                  </p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-[0.16em] text-ink-400">{label}</p>
      <p className="mt-1 font-display text-2xl text-signal">{value}</p>
    </div>
  );
}

function fmt(n: number, currency: string) {
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: currency.length === 3 ? currency : "USD",
      maximumFractionDigits: 0,
    }).format(n);
  } catch {
    return `${currency} ${n.toLocaleString()}`;
  }
}
