"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AlertForm } from "@/components/AlertForm";
import { InsightsPanel } from "@/components/InsightsPanel";
import { JobCard } from "@/components/JobCard";
import { LoadingProgress } from "@/components/LoadingProgress";
import { ResumeUpload } from "@/components/ResumeUpload";
import { SearchForm } from "@/components/SearchForm";
import { api, getUserId } from "@/lib/api";
import type { RankedJob, SearchCriteria, SearchResponse } from "@/types";

export default function HomePage() {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({ percent: 0, message: "" });
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sort, setSort] = useState("score");
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [bookmarkMap, setBookmarkMap] = useState<Record<string, string>>({});
  const [loadingMore, setLoadingMore] = useState(false);
  const [health, setHealth] = useState<string | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    api
      .health()
      .then((h) =>
        setHealth(
          `Apify ${h.services.apify} · AI ${h.services.ai} · Cache ${h.services.cache} · DB ${h.services.database}`
        )
      )
      .catch(() => setHealth("API offline — start the backend on :4000"));

    const userId = getUserId();
    api
      .bookmarks(userId)
      .then((res) => {
        const map: Record<string, string> = {};
        const ids = new Set<string>();
        res.bookmarks.forEach((b) => {
          ids.add(b.job.id);
          map[b.job.id] = b.id;
        });
        setSavedIds(ids);
        setBookmarkMap(map);
      })
      .catch(() => undefined);
  }, []);

  const runProgressSimulation = useCallback(() => {
    const steps = [
      { percent: 12, message: "Queueing search…" },
      { percent: 28, message: "Running Apify job scraper actor…" },
      { percent: 48, message: "Waiting for actor completion…" },
      { percent: 66, message: "Fetching & cleaning dataset…" },
      { percent: 82, message: "AI ranking by relevance, salary, recency…" },
    ];
    let i = 0;
    setProgress(steps[0]);
    const timer = setInterval(() => {
      i += 1;
      if (i >= steps.length) {
        clearInterval(timer);
        return;
      }
      setProgress(steps[i]);
    }, 700);
    return () => clearInterval(timer);
  }, []);

  const handleSearch = async (
    criteria: SearchCriteria & { naturalLanguage?: string }
  ) => {
    setLoading(true);
    setError(null);
    setResult(null);
    const stop = runProgressSimulation();
    try {
      const res = await api.search({
        ...criteria,
        userId: getUserId(),
        page: 1,
        pageSize: 8,
        sort,
      });
      setProgress({ percent: 100, message: "Ranked results ready" });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      stop();
      setLoading(false);
    }
  };

  const handleNaturalSearch = async (query: string) => {
    setLoading(true);
    setError(null);
    setResult(null);
    const stop = runProgressSimulation();
    try {
      const res = await api.naturalSearch(query, getUserId());
      setProgress({ percent: 100, message: "Ranked results ready" });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      stop();
      setLoading(false);
    }
  };

  const loadMore = useCallback(async () => {
    if (!result?.hasMore || loadingMore || loading) return;
    setLoadingMore(true);
    try {
      const next = await api.getSearch(result.searchId, {
        page: result.page + 1,
        pageSize: result.pageSize,
        sort,
      });
      setResult((prev) =>
        prev
          ? {
              ...next,
              jobs: [...prev.jobs, ...next.jobs],
            }
          : next
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load more");
    } finally {
      setLoadingMore(false);
    }
  }, [result, loadingMore, loading, sort]);

  useEffect(() => {
    const node = sentinelRef.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) void loadMore();
      },
      { rootMargin: "240px" }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [loadMore]);

  const onSortChange = async (nextSort: string) => {
    setSort(nextSort);
    if (!result) return;
    setLoadingMore(true);
    try {
      const refreshed = await api.getSearch(result.searchId, {
        page: 1,
        pageSize: result.pageSize,
        sort: nextSort,
      });
      setResult(refreshed);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sort failed");
    } finally {
      setLoadingMore(false);
    }
  };

  const toggleSave = async (job: RankedJob) => {
    const userId = getUserId();
    if (savedIds.has(job.id)) {
      const bmId = bookmarkMap[job.id];
      if (bmId) await api.removeBookmark(userId, bmId);
      setSavedIds((prev) => {
        const next = new Set(prev);
        next.delete(job.id);
        return next;
      });
      setBookmarkMap((prev) => {
        const next = { ...prev };
        delete next[job.id];
        return next;
      });
      return;
    }
    const bm = await api.addBookmark(userId, job);
    setSavedIds((prev) => new Set(prev).add(job.id));
    setBookmarkMap((prev) => ({ ...prev, [job.id]: bm.id }));
  };

  const criteriaLabel = useMemo(() => {
    if (!result) return null;
    const c = result.criteria;
    return `${c.role} · ${c.location || "Anywhere"}`;
  }, [result]);

  return (
    <div>
      <section className="relative overflow-hidden border-b border-white/10">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-hero-radial"
        />
        <div
          aria-hidden
          className="animate-floaty pointer-events-none absolute -right-16 top-10 h-72 w-72 rounded-full bg-signal/10 blur-3xl"
        />
        <div className="relative mx-auto max-w-6xl px-4 pb-16 pt-14 sm:px-6 sm:pt-20">
          <p className="animate-rise mb-3 text-xs uppercase tracking-[0.28em] text-signal">
            AI-ranked opportunities
          </p>
          <h1 className="animate-rise font-display text-5xl leading-[0.95] tracking-tight text-mist sm:text-7xl">
            Scout
          </h1>
          <p className="animate-rise-delay mt-5 max-w-xl text-lg text-ink-200 sm:text-xl">
            Enter a role and place. We scrape the market, clean the noise, and
            surface the strongest matches first.
          </p>
          <div className="animate-rise-late mt-10 max-w-4xl">
            <SearchForm
              loading={loading}
              onSearch={handleSearch}
              onNaturalSearch={handleNaturalSearch}
            />
          </div>
          {health && (
            <p className="mt-4 text-xs text-ink-400">{health}</p>
          )}
        </div>
      </section>

      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-10 sm:px-6 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div>
          {loading && (
            <LoadingProgress
              percent={progress.percent}
              message={progress.message}
            />
          )}

          {error && (
            <div className="mb-6 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
              {error}
            </div>
          )}

          {result && !loading && (
            <>
              <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
                <div>
                  <h2 className="font-display text-3xl text-mist">
                    {result.total} ranked roles
                  </h2>
                  <p className="mt-1 text-sm text-ink-300">
                    {criteriaLabel}
                    {result.cached ? " · cached" : ""} · {result.mode} mode
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <label className="text-sm text-ink-300">
                    Sort{" "}
                    <select
                      value={sort}
                      onChange={(e) => void onSortChange(e.target.value)}
                      className="ml-1 rounded-md border border-white/10 bg-ink-950 px-2 py-1 text-mist"
                    >
                      <option value="score">AI score</option>
                      <option value="salary">Salary</option>
                      <option value="date">Date</option>
                      <option value="company">Company</option>
                      <option value="title">Title</option>
                    </select>
                  </label>
                  <a
                    href={api.exportCsvUrl(result.searchId)}
                    className="rounded-md border border-white/10 px-3 py-1 text-sm text-ink-200 hover:border-signal/40 hover:text-signal"
                  >
                    CSV
                  </a>
                  <a
                    href={api.exportPdfUrl(result.searchId)}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-md border border-white/10 px-3 py-1 text-sm text-ink-200 hover:border-signal/40 hover:text-signal"
                  >
                    PDF
                  </a>
                </div>
              </div>

              <div className="relative mb-8">
                <AlertForm criteria={result.criteria} />
              </div>

              <div>
                {result.jobs.map((job) => (
                  <JobCard
                    key={`${job.id}-${job.score}`}
                    job={job}
                    saved={savedIds.has(job.id)}
                    onToggleSave={toggleSave}
                  />
                ))}
              </div>

              <div ref={sentinelRef} className="h-8" />
              {loadingMore && (
                <p className="py-4 text-center text-sm text-ink-300">
                  Loading more…
                </p>
              )}
              {!result.hasMore && result.jobs.length > 0 && (
                <p className="py-6 text-center text-sm text-ink-400">
                  End of results
                </p>
              )}

              <InsightsPanel
                salary={result.insights?.salary}
                companies={result.insights?.companies}
              />
            </>
          )}

          {!result && !loading && !error && (
            <p className="text-ink-300">
              Start with a role search or try natural language like “Remote
              Python jobs in Europe paying over €80k”.
            </p>
          )}
        </div>

        <aside className="space-y-6 lg:sticky lg:top-6 lg:self-start">
          <ResumeUpload />
          <div className="rounded-xl border border-white/10 bg-ink-950/40 p-4 text-sm text-ink-300">
            <p className="font-display text-lg text-mist">How ranking works</p>
            <ul className="mt-3 list-disc space-y-1 pl-4">
              <li>Title & skills relevance</li>
              <li>Location / remote fit</li>
              <li>Company reputation</li>
              <li>Salary & recency</li>
              <li>Employment type match</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
