import { aiRankingService } from "../ai/rankingService.js";
import { apifyService } from "../apify/apifyService.js";
import { locationMatches } from "../apify/demoData.js";
import { cacheService } from "../cache/cacheService.js";
import { databaseService } from "../database/databaseService.js";
import { cleanAndDeduplicate } from "../jobs/normalize.js";
import type {
  CompanyTrend,
  RankedJob,
  ResumeProfile,
  SalaryInsight,
  SearchCriteria,
  SearchProgress,
  SearchResult,
  SortOption,
} from "../../types/index.js";
import { createId, hashCriteria } from "../../utils/helpers.js";
import { config } from "../../config/index.js";

const progressStore = new Map<string, SearchProgress>();
const CACHE_VERSION = "v3";

export class JobSearchService {
  getProgress(searchId: string): SearchProgress | null {
    return progressStore.get(searchId) ?? null;
  }

  async search(
    criteria: SearchCriteria,
    options: {
      userId?: string;
      forceRefresh?: boolean;
      resume?: ResumeProfile | null;
    } = {}
  ): Promise<SearchResult> {
    const userId = options.userId ?? criteria.userId ?? "anonymous";
    const cacheKey = `search:${CACHE_VERSION}:${hashCriteria(criteria)}:${options.resume?.skills?.join(",") ?? ""}`;

    if (!options.forceRefresh) {
      const cached = await cacheService.get<SearchResult>(cacheKey);
      if (cached) {
        return { ...cached, cached: true };
      }
    }

    const searchId = createId("search");
    const setProgress = async (progress: SearchProgress) => {
      progressStore.set(searchId, progress);
    };

    await setProgress({
      stage: "queued",
      message: "Search queued",
      percent: 5,
    });

    const { jobs: rawJobs, mode, runId } = await apifyService.scrapeJobs(
      criteria,
      setProgress
    );

    await setProgress({
      stage: "cleaning",
      message: "Cleaning and deduplicating listings…",
      percent: 68,
      runId,
    });

    let normalized = cleanAndDeduplicate(
      rawJobs,
      mode === "demo" ? "demo" : "apify"
    );

    // Hard location filter for both live + demo results
    if (criteria.location?.trim()) {
      const before = normalized.length;
      normalized = normalized.filter((job) =>
        locationMatches(job.location, job.workMode, criteria.location)
      );
      console.log(
        `[search] location filter "${criteria.location}": ${before} → ${normalized.length}`
      );
    }

    await setProgress({
      stage: "ranking",
      message: "AI ranking opportunities…",
      percent: 80,
      runId,
    });

    let resume = options.resume ?? null;
    if (!resume) {
      const stored = await databaseService.getResume(userId);
      if (stored) resume = { text: stored.text, skills: stored.skills };
    }

    const ranked = await aiRankingService.rankJobs(normalized, criteria, resume);

    const result: SearchResult = {
      searchId,
      criteria,
      jobs: ranked,
      total: ranked.length,
      cached: false,
      createdAt: new Date().toISOString(),
      mode,
      progress: {
        stage: "complete",
        message: "Done",
        percent: 100,
        runId,
      },
    };

    await setProgress(result.progress!);
    // Cache demo results briefly so bad scrapes don't stick for an hour
    const ttl =
      mode === "demo"
        ? Math.min(120, config.cacheTtlSeconds)
        : config.cacheTtlSeconds;
    await cacheService.set(cacheKey, result, ttl);
    await databaseService.saveSearchResult(result, userId);

    setTimeout(() => progressStore.delete(searchId), 10 * 60 * 1000);

    return result;
  }

  paginate(
    jobs: RankedJob[],
    opts: {
      page?: number;
      pageSize?: number;
      sort?: SortOption;
      workMode?: string;
      employmentType?: string;
      minScore?: number;
    }
  ): { jobs: RankedJob[]; total: number; page: number; pageSize: number; hasMore: boolean } {
    let filtered = [...jobs];

    if (opts.workMode && opts.workMode !== "any") {
      filtered = filtered.filter((j) => j.workMode === opts.workMode);
    }
    if (opts.employmentType && opts.employmentType !== "any") {
      filtered = filtered.filter((j) => j.employmentType === opts.employmentType);
    }
    if (typeof opts.minScore === "number") {
      filtered = filtered.filter((j) => j.score >= opts.minScore!);
    }

    filtered = sortJobs(filtered, opts.sort ?? "score");

    const page = Math.max(1, opts.page ?? 1);
    const pageSize = Math.min(50, Math.max(1, opts.pageSize ?? 10));
    const start = (page - 1) * pageSize;
    const slice = filtered.slice(start, start + pageSize);

    return {
      jobs: slice,
      total: filtered.length,
      page,
      pageSize,
      hasMore: start + pageSize < filtered.length,
    };
  }

  buildSalaryInsights(jobs: RankedJob[]): SalaryInsight | null {
    const withSalary = jobs.filter((j) => j.salaryMin || j.salaryMax);
    if (withSalary.length < 2) return null;

    const mids = withSalary.map(
      (j) => ((j.salaryMin ?? j.salaryMax!) + (j.salaryMax ?? j.salaryMin!)) / 2
    );
    mids.sort((a, b) => a - b);
    const currency = withSalary.find((j) => j.currency)?.currency ?? "USD";
    const sum = mids.reduce((a, b) => a + b, 0);
    const median = mids[Math.floor(mids.length / 2)];

    const byWorkMode: SalaryInsight["byWorkMode"] = {};
    for (const job of withSalary) {
      const key = job.workMode;
      const mid =
        ((job.salaryMin ?? job.salaryMax!) + (job.salaryMax ?? job.salaryMin!)) / 2;
      if (!byWorkMode[key]) byWorkMode[key] = { average: 0, count: 0 };
      byWorkMode[key].average += mid;
      byWorkMode[key].count += 1;
    }
    for (const key of Object.keys(byWorkMode)) {
      byWorkMode[key].average = Math.round(
        byWorkMode[key].average / byWorkMode[key].count
      );
    }

    const companyMap = new Map<string, { total: number; count: number }>();
    for (const job of withSalary) {
      const mid =
        ((job.salaryMin ?? job.salaryMax!) + (job.salaryMax ?? job.salaryMin!)) / 2;
      const entry = companyMap.get(job.company) ?? { total: 0, count: 0 };
      entry.total += mid;
      entry.count += 1;
      companyMap.set(job.company, entry);
    }

    return {
      currency,
      min: Math.round(mids[0]),
      max: Math.round(mids[mids.length - 1]),
      median: Math.round(median),
      average: Math.round(sum / mids.length),
      sampleSize: mids.length,
      byWorkMode,
      byCompany: [...companyMap.entries()]
        .map(([company, v]) => ({
          company,
          average: Math.round(v.total / v.count),
          count: v.count,
        }))
        .sort((a, b) => b.average - a.average)
        .slice(0, 8),
    };
  }

  buildCompanyTrends(jobs: RankedJob[]): CompanyTrend[] {
    const map = new Map<
      string,
      { openings: number; scoreSum: number; remote: number; roles: Map<string, number> }
    >();

    for (const job of jobs) {
      const entry = map.get(job.company) ?? {
        openings: 0,
        scoreSum: 0,
        remote: 0,
        roles: new Map(),
      };
      entry.openings += 1;
      entry.scoreSum += job.score;
      if (job.workMode === "remote") entry.remote += 1;
      entry.roles.set(job.title, (entry.roles.get(job.title) ?? 0) + 1);
      map.set(job.company, entry);
    }

    return [...map.entries()]
      .map(([company, v]) => ({
        company,
        openings: v.openings,
        averageScore: Math.round(v.scoreSum / v.openings),
        remoteShare: Math.round((v.remote / v.openings) * 100),
        topRoles: [...v.roles.entries()]
          .sort((a, b) => b[1] - a[1])
          .slice(0, 3)
          .map(([t]) => t),
      }))
      .sort((a, b) => b.openings - a.openings || b.averageScore - a.averageScore)
      .slice(0, 10);
  }

  recommendationsFromHistory(history: SearchResult[], limit = 8): RankedJob[] {
    const seen = new Set<string>();
    const pooled: RankedJob[] = [];
    for (const search of history) {
      for (const job of search.jobs) {
        if (seen.has(job.id)) continue;
        seen.add(job.id);
        pooled.push(job);
      }
    }
    return pooled.sort((a, b) => b.score - a.score).slice(0, limit);
  }
}

function sortJobs(jobs: RankedJob[], sort: SortOption): RankedJob[] {
  const copy = [...jobs];
  switch (sort) {
    case "salary":
      return copy.sort(
        (a, b) => (b.salaryMax ?? b.salaryMin ?? 0) - (a.salaryMax ?? a.salaryMin ?? 0)
      );
    case "date":
      return copy.sort(
        (a, b) =>
          new Date(b.postedAt ?? 0).getTime() - new Date(a.postedAt ?? 0).getTime()
      );
    case "company":
      return copy.sort((a, b) => a.company.localeCompare(b.company));
    case "title":
      return copy.sort((a, b) => a.title.localeCompare(b.title));
    case "score":
    default:
      return copy.sort((a, b) => b.score - a.score);
  }
}

export function jobsToCsv(jobs: RankedJob[]): string {
  const headers = [
    "title",
    "company",
    "location",
    "salary",
    "employmentType",
    "workMode",
    "postedAt",
    "score",
    "reason",
    "applyUrl",
  ];
  const escape = (v: unknown) => {
    const s = String(v ?? "");
    if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };
  const rows = jobs.map((j) =>
    [
      j.title,
      j.company,
      j.location,
      j.salary,
      j.employmentType,
      j.workMode,
      j.postedAt,
      j.score,
      j.reason,
      j.applyUrl,
    ]
      .map(escape)
      .join(",")
  );
  return [headers.join(","), ...rows].join("\n");
}

export const jobSearchService = new JobSearchService();
