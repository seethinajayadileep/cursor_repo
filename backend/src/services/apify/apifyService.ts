import { ApifyClient } from "apify-client";
import { config, hasApify } from "../../config/index.js";
import type { RawJob, SearchCriteria, SearchProgress } from "../../types/index.js";
import { createId, sleep } from "../../utils/helpers.js";
import { filterDemoJobs } from "./demoData.js";

export type ProgressCallback = (progress: SearchProgress) => void | Promise<void>;

export class ApifyService {
  private client: ApifyClient | null = null;

  constructor() {
    if (hasApify) {
      this.client = new ApifyClient({ token: config.apifyToken });
    }
  }

  isLive(): boolean {
    return Boolean(this.client);
  }

  async scrapeJobs(
    criteria: SearchCriteria,
    onProgress?: ProgressCallback
  ): Promise<{ jobs: RawJob[]; mode: "live" | "demo"; runId: string }> {
    if (!this.client) {
      return this.scrapeDemo(criteria, onProgress);
    }

    try {
      await onProgress?.({
        stage: "scraping",
        message: "Starting Apify job scraper actor…",
        percent: 10,
      });

      const input = this.buildActorInput(criteria);
      console.log("[apify] actor input:", JSON.stringify(input));

      const run = await this.client.actor(config.apifyActorId).call(input, {
        waitSecs: 180,
      });

      await onProgress?.({
        stage: "scraping",
        message: "Apify actor finished — fetching dataset…",
        percent: 55,
        runId: run.id,
      });

      const { items } = await this.client
        .dataset(run.defaultDatasetId)
        .listItems({ limit: 100 });
      const jobs = (items as RawJob[]) ?? [];
      console.log(`[apify] run=${run.id} status=${run.status} items=${jobs.length}`);

      if (jobs.length === 0) {
        console.warn("[apify] Actor returned 0 jobs — falling back to demo");
        const demo = await this.scrapeDemo(criteria, onProgress);
        return { ...demo, mode: "demo" };
      }

      return { jobs, mode: "live", runId: run.id };
    } catch (error) {
      console.warn("[apify] Live scrape failed, using demo data:", error);
      return this.scrapeDemo(criteria, onProgress);
    }
  }

  private buildActorInput(criteria: SearchCriteria) {
    const role = (criteria.role || "Software Engineer").trim();
    const location = (criteria.location || "").trim();
    const linkedInUrl = buildLinkedInJobsUrl(role, location, criteria.workMode);

    // Support common LinkedIn job scraper actor input shapes
    return {
      // URL-based actors (curious_coder/linkedin-jobs-scraper and similar)
      urls: [linkedInUrl],
      startUrls: [{ url: linkedInUrl }],
      // Keyword-based actors
      queries: [`${role} ${location}`.trim()],
      keyword: role,
      keywords: role,
      location,
      locations: location ? [location] : [],
      count: 40,
      maxItems: 40,
      rows: 40,
      scrapeCompany: false,
      proxy: {
        useApifyProxy: true,
      },
      experienceLevel:
        criteria.experienceLevel === "any" ? undefined : criteria.experienceLevel,
      contractType:
        criteria.employmentType && criteria.employmentType !== "any"
          ? criteria.employmentType
          : undefined,
      remote:
        criteria.workMode === "remote"
          ? "remote"
          : criteria.workMode === "hybrid"
            ? "hybrid"
            : undefined,
    };
  }

  private async scrapeDemo(
    criteria: SearchCriteria,
    onProgress?: ProgressCallback
  ): Promise<{ jobs: RawJob[]; mode: "live" | "demo"; runId: string }> {
    const runId = createId("demo");

    await onProgress?.({
      stage: "scraping",
      message: "Using demo dataset (Apify returned no usable jobs)…",
      percent: 15,
      runId,
    });
    await sleep(300);

    await onProgress?.({
      stage: "scraping",
      message: "Filtering demo listings by role and location…",
      percent: 40,
      runId,
    });
    await sleep(300);

    const filtered = filterDemoJobs({
      role: criteria.role || criteria.naturalLanguage || "software",
      location: criteria.location || "",
      experienceLevel: criteria.experienceLevel,
      employmentType: criteria.employmentType,
      workMode: criteria.workMode,
      salaryMin: criteria.salaryMin,
      salaryMax: criteria.salaryMax,
      companySize: criteria.companySize,
    });

    // Relax role only — never drop the location filter
    const jobs: RawJob[] =
      filtered.length > 0
        ? filtered
        : filterDemoJobs({
            role: "engineer",
            location: criteria.location || "",
            experienceLevel: criteria.experienceLevel,
            employmentType: criteria.employmentType,
            workMode: criteria.workMode,
            salaryMin: criteria.salaryMin,
            salaryMax: criteria.salaryMax,
            companySize: criteria.companySize,
          });

    await onProgress?.({
      stage: "scraping",
      message:
        jobs.length > 0
          ? `Fetched ${jobs.length} demo job listings`
          : `No demo listings matched ${criteria.location || "that search"}`,
      percent: 60,
      runId,
    });

    return { jobs, mode: "demo", runId };
  }
}

function buildLinkedInJobsUrl(
  role: string,
  location: string,
  workMode?: string
): string {
  const params = new URLSearchParams();
  params.set("keywords", role);
  if (location) params.set("location", location);
  if (workMode === "remote") params.set("f_WT", "2");
  params.set("f_TPR", "r604800"); // past week
  return `https://www.linkedin.com/jobs/search/?${params.toString()}`;
}

export const apifyService = new ApifyService();
