import { Router } from "express";
import multer from "multer";
import { aiRankingService } from "../services/ai/rankingService.js";
import { databaseService } from "../services/database/databaseService.js";
import { extractSkillsFromText } from "../services/jobs/normalize.js";
import {
  jobSearchService,
  jobsToCsv,
} from "../services/jobs/searchService.js";
import { cacheService } from "../services/cache/cacheService.js";
import { apifyService } from "../services/apify/apifyService.js";
import { extractResumeText } from "../services/resume/parseResume.js";
import { hasApify, hasOpenAI, hasTelegram } from "../config/index.js";
import type { RankedJob, SearchCriteria } from "../types/index.js";
import {
  alertSchema,
  bookmarkSchema,
  nlSearchSchema,
  searchBodySchema,
} from "../middleware/validation.js";

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024 },
  fileFilter: (_req, file, cb) => {
    const name = file.originalname.toLowerCase();
    const mime = (file.mimetype || "").toLowerCase();
    const ok =
      mime.includes("pdf") ||
      mime.includes("text") ||
      mime.includes("markdown") ||
      name.endsWith(".pdf") ||
      name.endsWith(".txt") ||
      name.endsWith(".md") ||
      name.endsWith(".csv");
    if (!ok) {
      cb(new Error("Only PDF, TXT, MD, or CSV resumes are supported"));
      return;
    }
    cb(null, true);
  },
});

export const apiRouter = Router();

apiRouter.get("/health", (_req, res) => {
  res.json({
    ok: true,
    services: {
      apify: hasApify && apifyService.isLive() ? "live" : "demo",
      ai: hasOpenAI && aiRankingService.isLive() ? "openai" : "heuristic",
      cache: cacheService.mode(),
      database: databaseService.mode(),
      telegram: hasTelegram ? "configured" : "off",
    },
  });
});

apiRouter.post("/search", async (req, res, next) => {
  try {
    const parsed = searchBodySchema.parse(req.body);
    let criteria: SearchCriteria = {
      role: parsed.role ?? "",
      location: parsed.location ?? "",
      experienceLevel: parsed.experienceLevel,
      employmentType: parsed.employmentType,
      salaryMin: parsed.salaryMin,
      salaryMax: parsed.salaryMax,
      workMode: parsed.workMode,
      companySize: parsed.companySize,
      naturalLanguage: parsed.naturalLanguage,
      skills: parsed.skills,
      userId: parsed.userId,
    };

    if (parsed.naturalLanguage && !parsed.role) {
      const extracted = await aiRankingService.parseNaturalLanguage(
        parsed.naturalLanguage
      );
      criteria = {
        ...criteria,
        ...extracted,
        role: extracted.role || "Software Engineer",
        location: extracted.location || criteria.location || "Remote",
      };
    }

    if (!criteria.role) {
      res.status(400).json({ error: "role or naturalLanguage is required" });
      return;
    }

    const result = await jobSearchService.search(criteria, {
      userId: parsed.userId,
      forceRefresh: parsed.forceRefresh,
    });

    const page = jobSearchService.paginate(result.jobs, {
      page: parsed.page ?? 1,
      pageSize: parsed.pageSize ?? 10,
      sort: parsed.sort ?? "score",
    });

    res.json({
      ...result,
      jobs: page.jobs,
      total: page.total,
      page: page.page,
      pageSize: page.pageSize,
      hasMore: page.hasMore,
      allJobIds: result.jobs.map((j) => j.id),
      insights: {
        salary: jobSearchService.buildSalaryInsights(result.jobs),
        companies: jobSearchService.buildCompanyTrends(result.jobs),
      },
    });
  } catch (error) {
    next(error);
  }
});

apiRouter.post("/search/natural", async (req, res, next) => {
  try {
    const parsed = nlSearchSchema.parse(req.body);
    const extracted = await aiRankingService.parseNaturalLanguage(parsed.query);
    const criteria: SearchCriteria = {
      role: extracted.role || "Software Engineer",
      location: extracted.location || "Remote",
      experienceLevel: extracted.experienceLevel ?? "any",
      employmentType: extracted.employmentType ?? "any",
      salaryMin: extracted.salaryMin,
      salaryMax: extracted.salaryMax,
      workMode: extracted.workMode ?? "any",
      companySize: extracted.companySize ?? "any",
      skills: extracted.skills,
      naturalLanguage: parsed.query,
      userId: parsed.userId,
    };

    const result = await jobSearchService.search(criteria, {
      userId: parsed.userId,
      forceRefresh: parsed.forceRefresh,
    });

    const page = jobSearchService.paginate(result.jobs, {
      page: 1,
      pageSize: 10,
      sort: "score",
    });

    res.json({
      ...result,
      criteria,
      jobs: page.jobs,
      total: page.total,
      page: page.page,
      pageSize: page.pageSize,
      hasMore: page.hasMore,
      insights: {
        salary: jobSearchService.buildSalaryInsights(result.jobs),
        companies: jobSearchService.buildCompanyTrends(result.jobs),
      },
    });
  } catch (error) {
    next(error);
  }
});

apiRouter.get("/search/:searchId", async (req, res, next) => {
  try {
    const result = await databaseService.getSearch(req.params.searchId);
    if (!result) {
      res.status(404).json({ error: "Search not found" });
      return;
    }

    const page = Number(req.query.page ?? 1);
    const pageSize = Number(req.query.pageSize ?? 10);
    const sort = String(req.query.sort ?? "score") as
      | "score"
      | "salary"
      | "date"
      | "company"
      | "title";
    const workMode = req.query.workMode?.toString();
    const employmentType = req.query.employmentType?.toString();
    const minScore = req.query.minScore
      ? Number(req.query.minScore)
      : undefined;

    const paged = jobSearchService.paginate(result.jobs, {
      page,
      pageSize,
      sort,
      workMode,
      employmentType,
      minScore,
    });

    res.json({
      ...result,
      jobs: paged.jobs,
      total: paged.total,
      page: paged.page,
      pageSize: paged.pageSize,
      hasMore: paged.hasMore,
      insights: {
        salary: jobSearchService.buildSalaryInsights(result.jobs),
        companies: jobSearchService.buildCompanyTrends(result.jobs),
      },
    });
  } catch (error) {
    next(error);
  }
});

apiRouter.get("/search/:searchId/progress", (req, res) => {
  const progress = jobSearchService.getProgress(req.params.searchId);
  res.json(progress ?? { stage: "complete", message: "Done", percent: 100 });
});

apiRouter.get("/searches", async (req, res, next) => {
  try {
    const limit = Number(req.query.limit ?? 20);
    const searches = await databaseService.listSearches(limit);
    res.json({
      searches: searches.map((s) => ({
        searchId: s.searchId,
        criteria: s.criteria,
        total: s.total,
        createdAt: s.createdAt,
        mode: s.mode,
      })),
    });
  } catch (error) {
    next(error);
  }
});

apiRouter.get("/recommendations", async (req, res, next) => {
  try {
    const history = await databaseService.listSearches(10);
    const jobs = jobSearchService.recommendationsFromHistory(history);
    res.json({ jobs });
  } catch (error) {
    next(error);
  }
});

apiRouter.post("/bookmarks", async (req, res, next) => {
  try {
    const parsed = bookmarkSchema.parse(req.body);
    const bookmark = await databaseService.addBookmark(
      parsed.userId,
      parsed.job as unknown as RankedJob
    );
    res.status(201).json(bookmark);
  } catch (error) {
    next(error);
  }
});

apiRouter.get("/bookmarks", async (req, res, next) => {
  try {
    const userId = String(req.query.userId ?? "anonymous");
    const bookmarks = await databaseService.listBookmarks(userId);
    res.json({ bookmarks });
  } catch (error) {
    next(error);
  }
});

apiRouter.delete("/bookmarks/:id", async (req, res, next) => {
  try {
    const userId = String(req.query.userId ?? "anonymous");
    const ok = await databaseService.removeBookmark(userId, req.params.id);
    res.json({ deleted: ok });
  } catch (error) {
    next(error);
  }
});

apiRouter.post("/alerts", async (req, res, next) => {
  try {
    const parsed = alertSchema.parse(req.body);
    const saved = await databaseService.saveSearchAlert(
      parsed.userId,
      parsed.criteria as unknown as SearchCriteria,
      parsed.email
    );
    res.status(201).json({
      ...saved,
      message: `Email alerts registered for ${parsed.email} (delivery is stubbed in this demo).`,
    });
  } catch (error) {
    next(error);
  }
});

apiRouter.get("/alerts", async (req, res, next) => {
  try {
    const userId = String(req.query.userId ?? "anonymous");
    const alerts = await databaseService.listSavedSearches(userId);
    res.json({ alerts });
  } catch (error) {
    next(error);
  }
});

apiRouter.post("/resume", upload.single("resume"), async (req, res, next) => {
  try {
    const userId = String(req.body.userId ?? "anonymous");
    const pasted = String(req.body.text ?? "");
    const { text, source } = await extractResumeText(req.file, pasted);

    if (!text.trim()) {
      res.status(400).json({
        error:
          "Resume text or file required. For PDFs, use a text-based PDF (not a scanned image).",
      });
      return;
    }

    const skills = extractSkillsFromText(text);
    await databaseService.saveResume(userId, text.slice(0, 50000), skills);
    res.json({
      userId,
      skills,
      characters: text.length,
      source,
      message:
        source === "pdf"
          ? "PDF resume parsed and saved for personalized ranking"
          : "Resume saved for personalized ranking",
    });
  } catch (error) {
    next(error);
  }
});

apiRouter.get("/resume", async (req, res, next) => {
  try {
    const userId = String(req.query.userId ?? "anonymous");
    const resume = await databaseService.getResume(userId);
    res.json({ resume });
  } catch (error) {
    next(error);
  }
});

apiRouter.get("/export/:searchId.csv", async (req, res, next) => {
  try {
    const result = await databaseService.getSearch(req.params.searchId);
    if (!result) {
      res.status(404).json({ error: "Search not found" });
      return;
    }
    const csv = jobsToCsv(result.jobs);
    res.setHeader("Content-Type", "text/csv");
    res.setHeader(
      "Content-Disposition",
      `attachment; filename="jobs-${req.params.searchId}.csv"`
    );
    res.send(csv);
  } catch (error) {
    next(error);
  }
});

apiRouter.get("/export/:searchId.pdf", async (req, res, next) => {
  try {
    const result = await databaseService.getSearch(req.params.searchId);
    if (!result) {
      res.status(404).json({ error: "Search not found" });
      return;
    }
    // Lightweight printable HTML that browsers can Save as PDF
    const rows = result.jobs
      .map(
        (j) => `
      <article style="margin:0 0 18px;padding:0 0 12px;border-bottom:1px solid #ddd">
        <h2 style="margin:0 0 4px;font-size:16px">${escapeHtml(j.title)} — ${escapeHtml(j.company)}</h2>
        <p style="margin:0;color:#444;font-size:12px">${escapeHtml(j.location)} · ${escapeHtml(j.salary ?? "Salary n/a")} · Score ${j.score}</p>
        <p style="margin:6px 0 0;font-size:12px">${escapeHtml(j.reason)}</p>
        <p style="margin:6px 0 0;font-size:12px;white-space:pre-wrap">${escapeHtml(j.summary)}</p>
      </article>`
      )
      .join("");

    const html = `<!DOCTYPE html><html><head><meta charset="utf-8"><title>Job results</title></head>
      <body style="font-family:Georgia,serif;max-width:720px;margin:24px auto;padding:0 16px;color:#111">
        <h1 style="font-size:22px">Scout — Ranked Jobs</h1>
        <p style="color:#555;font-size:13px">${escapeHtml(result.criteria.role)} · ${escapeHtml(result.criteria.location)} · ${result.total} roles</p>
        ${rows}
      </body></html>`;

    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.setHeader(
      "Content-Disposition",
      `inline; filename="jobs-${req.params.searchId}.html"`
    );
    res.send(html);
  } catch (error) {
    next(error);
  }
});

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
