import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { cleanAndDeduplicate } from "./normalize.js";
import {
  AiRankingService,
  heuristicParseNaturalLanguage,
} from "../ai/rankingService.js";
import { jobsToCsv } from "./searchService.js";
import type { NormalizedJob, RankedJob } from "../../types/index.js";

describe("normalize", () => {
  it("deduplicates jobs by title+company+location", () => {
    const jobs = cleanAndDeduplicate([
      {
        title: "Software Engineer",
        company: "Acme",
        location: "Remote",
        description: "Build APIs with TypeScript and Node.js",
      },
      {
        title: "Software Engineer",
        company: "Acme",
        location: "Remote",
        description: "Duplicate",
      },
      {
        title: "Product Manager",
        company: "Acme",
        location: "London",
        description: "Ship product",
      },
    ]);
    assert.equal(jobs.length, 2);
    assert.ok(jobs[0].skills.includes("TypeScript"));
  });
});

describe("natural language parse", () => {
  it("extracts remote python europe salary", () => {
    const parsed = heuristicParseNaturalLanguage(
      "Remote Python jobs in Europe paying over €80k"
    );
    assert.equal(parsed.workMode, "remote");
    assert.match(parsed.role ?? "", /python/i);
    assert.match(parsed.location ?? "", /europe/i);
    assert.equal(parsed.salaryMin, 80000);
  });
});

describe("apply link resolution", () => {
  it("prefers external company apply URL over LinkedIn", async () => {
    const { resolveApplyLinks } = await import("./normalize.js");
    const links = resolveApplyLinks({
      applyUrl: "",
      link: "https://www.linkedin.com/jobs/view/123",
      externalApplyUrl: "https://jobs.apple.com/en-us/details/200",
    });
    assert.equal(links.isExternalApply, true);
    assert.equal(links.applyUrl, "https://jobs.apple.com/en-us/details/200");
    assert.match(links.linkedinUrl ?? "", /linkedin\.com/);
  });

  it("falls back to LinkedIn when no external URL exists", async () => {
    const { resolveApplyLinks } = await import("./normalize.js");
    const links = resolveApplyLinks({
      applyUrl: "https://in.linkedin.com/jobs/view/456",
      link: "https://in.linkedin.com/jobs/view/456",
    });
    assert.equal(links.isExternalApply, false);
    assert.match(links.applyUrl ?? "", /linkedin\.com/);
  });
});

describe("ai heuristic ranking", () => {
  it("scores remote title matches higher", () => {
    const ai = new AiRankingService();
    const base: NormalizedJob = {
      id: "1",
      title: "Senior Software Engineer",
      company: "Stripe",
      location: "Remote",
      salary: "$200k",
      salaryMin: 200000,
      salaryMax: 200000,
      currency: "USD",
      employmentType: "full-time",
      workMode: "remote",
      description: "TypeScript distributed systems",
      postedAt: new Date().toISOString(),
      applyUrl: "https://example.com",
      linkedinUrl: null,
      isExternalApply: true,
      companyLogo: null,
      companySize: "large",
      skills: ["TypeScript", "Go"],
      experienceLevel: "senior",
      source: "test",
    };
    const enrichment = ai.heuristicEnrich(base, {
      role: "Software Engineer",
      location: "Remote",
      workMode: "remote",
      skills: ["TypeScript"],
    });
    assert.ok(enrichment.score >= 70);
    assert.ok(enrichment.summary.split("\n").length >= 3);
  });
});

describe("csv export", () => {
  it("creates header row", () => {
    const csv = jobsToCsv([
      {
        id: "1",
        title: 'Engineer, "Platform"',
        company: "X",
        location: "Remote",
        salary: null,
        salaryMin: null,
        salaryMax: null,
        currency: null,
        employmentType: "full-time",
        workMode: "remote",
        description: "",
        postedAt: null,
        applyUrl: null,
        linkedinUrl: null,
        isExternalApply: false,
        companyLogo: null,
        companySize: null,
        skills: [],
        experienceLevel: null,
        source: "test",
        score: 90,
        reason: "Great",
        summary: "a\nb\nc",
        requiredSkills: [],
        missingSkills: [],
        resumeTips: [],
        interviewDifficulty: "moderate",
      } as RankedJob,
    ]);
    assert.match(csv, /^title,company/);
    assert.match(csv, /""Platform""/);
  });
});
