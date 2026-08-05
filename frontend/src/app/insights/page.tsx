"use client";

import { useEffect, useState } from "react";
import { InsightsPanel } from "@/components/InsightsPanel";
import { JobCard } from "@/components/JobCard";
import { api } from "@/lib/api";
import type { CompanyTrend, RankedJob, SalaryInsight, SearchCriteria } from "@/types";

export default function InsightsPage() {
  const [history, setHistory] = useState<
    Array<{
      searchId: string;
      criteria: SearchCriteria;
      total: number;
      createdAt: string;
      mode: string;
    }>
  >([]);
  const [recs, setRecs] = useState<RankedJob[]>([]);
  const [salary, setSalary] = useState<SalaryInsight | null>(null);
  const [companies, setCompanies] = useState<CompanyTrend[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [searches, recommendations] = await Promise.all([
          api.listSearches(),
          api.recommendations(),
        ]);
        setHistory(searches.searches);
        setRecs(recommendations.jobs);

        if (searches.searches[0]) {
          const latest = await api.getSearch(searches.searches[0].searchId, {
            page: 1,
            pageSize: 5,
          });
          setSalary(latest.insights?.salary ?? null);
          setCompanies(latest.insights?.companies ?? []);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load insights");
      }
    })();
  }, []);

  return (
    <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-4xl text-mist">Insights</h1>
      <p className="mt-2 max-w-2xl text-ink-300">
        Salary analytics, company hiring trends, and recommendations from your
        recent searches.
      </p>
      {error && <p className="mt-4 text-sm text-red-300">{error}</p>}

      <div className="mt-10">
        <InsightsPanel salary={salary} companies={companies} />
      </div>

      <section className="mt-12">
        <h2 className="font-display text-2xl text-mist">Recommended for you</h2>
        <p className="mt-1 text-sm text-ink-300">
          Based on previous search history.
        </p>
        <div className="mt-6">
          {recs.length === 0 ? (
            <p className="text-ink-400">Run a few searches to unlock recommendations.</p>
          ) : (
            recs.map((job) => <JobCard key={job.id} job={job} />)
          )}
        </div>
      </section>

      <section className="mt-12">
        <h2 className="font-display text-2xl text-mist">Recent searches</h2>
        <ul className="mt-4 divide-y divide-white/10">
          {history.map((s) => (
            <li key={s.searchId} className="flex flex-wrap justify-between gap-2 py-3 text-sm">
              <div>
                <p className="text-mist">
                  {s.criteria.role} · {s.criteria.location}
                </p>
                <p className="text-xs text-ink-400">
                  {new Date(s.createdAt).toLocaleString()} · {s.mode}
                </p>
              </div>
              <p className="text-ink-300">{s.total} roles</p>
            </li>
          ))}
          {history.length === 0 && (
            <li className="py-3 text-ink-400">No history yet.</li>
          )}
        </ul>
      </section>
    </div>
  );
}
