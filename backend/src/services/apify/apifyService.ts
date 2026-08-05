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
      const run = await this.client.actor(config.apifyActorId).call(input, {
        waitSecs: 180,
      });

      await onProgress?.({
        stage: "scraping",
        message: "Apify actor finished — fetching dataset…",
        percent: 55,
        runId: run.id,
      });

      const { items } = await this.client.dataset(run.defaultDatasetId).listItems();
      const jobs = (items as RawJob[]) ?? [];

      if (jobs.length === 0) {
        // Fall back to demo if actor returned nothing useful
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
    const queries = [criteria.role];
    if (criteria.location) queries.push(criteria.location);

    return {
      queries: [`${criteria.role} ${criteria.location}`.trim()],
      locations: criteria.location ? [criteria.location] : [],
      maxItems: 40,
      count: 40,
      experienceLevel: criteria.experienceLevel === "any" ? undefined : criteria.experienceLevel,
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
      message: "Running demo scraper (no Apify token configured)…",
      percent: 15,
      runId,
    });
    await sleep(400);

    await onProgress?.({
      stage: "scraping",
      message: "Collecting listings from demo sources…",
      percent: 40,
      runId,
    });
    await sleep(500);

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

    // Ensure we always return something useful in demo mode
    const jobs: RawJob[] =
      filtered.length > 0
        ? filtered
        : filterDemoJobs({ role: "engineer", location: "" });

    await onProgress?.({
      stage: "scraping",
      message: `Fetched ${jobs.length} job listings`,
      percent: 60,
      runId,
    });

    return { jobs, mode: "demo", runId };
  }
}

export const apifyService = new ApifyService();
