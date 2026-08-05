import OpenAI from "openai";
import { config, hasOpenAI } from "../../config/index.js";
import type {
  AiEnrichment,
  NormalizedJob,
  RankedJob,
  ResumeProfile,
  SearchCriteria,
} from "../../types/index.js";
import { clamp } from "../../utils/helpers.js";
import { extractSkillsFromText } from "../jobs/normalize.js";

const REPUTABLE = new Set(
  [
    "stripe",
    "notion",
    "figma",
    "vercel",
    "airbnb",
    "spotify",
    "datadog",
    "cloudflare",
    "shopify",
    "anthropic",
    "deepmind",
    "google",
    "meta",
    "apple",
    "amazon",
    "microsoft",
    "netflix",
    "uber",
    "revolut",
    "razorpay",
    "canva",
    "okta",
    "duolingo",
    "linear",
    "freshworks",
  ].map((s) => s.toLowerCase())
);

export class AiRankingService {
  private client: OpenAI | null = null;

  constructor() {
    if (hasOpenAI) {
      this.client = new OpenAI({ apiKey: config.openaiApiKey });
    }
  }

  isLive(): boolean {
    return Boolean(this.client);
  }

  async rankJobs(
    jobs: NormalizedJob[],
    criteria: SearchCriteria,
    resume?: ResumeProfile | null
  ): Promise<RankedJob[]> {
    if (jobs.length === 0) return [];

    if (this.client && jobs.length <= 20) {
      try {
        return await this.rankWithLlm(jobs, criteria, resume);
      } catch (error) {
        console.warn("[ai] LLM ranking failed, using heuristic:", error);
      }
    }

    return jobs
      .map((job) => ({ ...job, ...this.heuristicEnrich(job, criteria, resume) }))
      .sort((a, b) => b.score - a.score);
  }

  async parseNaturalLanguage(query: string): Promise<Partial<SearchCriteria>> {
    let parsed: Partial<SearchCriteria> = {};
    if (this.client) {
      try {
        const completion = await this.client.chat.completions.create({
          model: config.openaiModel,
          temperature: 0,
          response_format: { type: "json_object" },
          messages: [
            {
              role: "system",
              content:
                'Extract job search criteria as JSON with keys: role, location, experienceLevel, employmentType, salaryMin, salaryMax, workMode, companySize, skills (string[]). Use null for unknown. experienceLevel one of internship|entry|mid|senior|lead|executive|any. workMode one of remote|hybrid|onsite|any. role must be a full job title like "Python Developer", never a bare language name.',
            },
            { role: "user", content: query },
          ],
        });
        const text = completion.choices[0]?.message?.content ?? "{}";
        parsed = JSON.parse(text) as Partial<SearchCriteria>;
      } catch (error) {
        console.warn("[ai] NL parse failed:", error);
        parsed = heuristicParseNaturalLanguage(query);
      }
    } else {
      parsed = heuristicParseNaturalLanguage(query);
    }
    return polishParsedCriteria(parsed, query);
  }

  private async rankWithLlm(
    jobs: NormalizedJob[],
    criteria: SearchCriteria,
    resume?: ResumeProfile | null
  ): Promise<RankedJob[]> {
    const payload = jobs.map((j) => ({
      id: j.id,
      title: j.title,
      company: j.company,
      location: j.location,
      salary: j.salary,
      employmentType: j.employmentType,
      workMode: j.workMode,
      postedAt: j.postedAt,
      skills: j.skills,
      description: j.description.slice(0, 600),
    }));

    const completion = await this.client!.chat.completions.create({
      model: config.openaiModel,
      temperature: 0.2,
      response_format: { type: "json_object" },
      messages: [
        {
          role: "system",
          content: `You rank job listings for a candidate. Return JSON: {"rankings":[{"id":"...","score":0-100,"reason":"one sentence","summary":"3 short lines separated by \\n","requiredSkills":[],"missingSkills":[],"resumeTips":["...","..."],"interviewDifficulty":"easy|moderate|hard|very-hard"}]}. Score using title relevance, skills match, location match, company reputation, salary, recency, remote preference, employment type.`,
        },
        {
          role: "user",
          content: JSON.stringify({
            criteria,
            resumeSkills: resume?.skills ?? [],
            jobs: payload,
          }),
        },
      ],
    });

    const parsed = JSON.parse(
      completion.choices[0]?.message?.content ?? '{"rankings":[]}'
    ) as { rankings: Array<AiEnrichment & { id: string }> };

    const byId = new Map(parsed.rankings.map((r) => [r.id, r]));

    return jobs
      .map((job) => {
        const ai = byId.get(job.id);
        if (ai) {
          return {
            ...job,
            score: clamp(Number(ai.score) || 0, 0, 100),
            reason: ai.reason || "Strong overall match.",
            summary: ai.summary || job.description.slice(0, 220),
            requiredSkills: ai.requiredSkills?.length
              ? ai.requiredSkills
              : job.skills,
            missingSkills: ai.missingSkills ?? [],
            resumeTips: ai.resumeTips?.length
              ? ai.resumeTips
              : ["Tailor your resume to highlight matching skills."],
            interviewDifficulty: ai.interviewDifficulty ?? "moderate",
          };
        }
        return { ...job, ...this.heuristicEnrich(job, criteria, resume) };
      })
      .sort((a, b) => b.score - a.score);
  }

  heuristicEnrich(
    job: NormalizedJob,
    criteria: SearchCriteria,
    resume?: ResumeProfile | null
  ): AiEnrichment {
    const role = (criteria.role || "").toLowerCase();
    const location = (criteria.location || "").toLowerCase();
    const title = job.title.toLowerCase();
    const desc = job.description.toLowerCase();
    const userSkills = new Set(
      [
        ...(criteria.skills ?? []),
        ...(resume?.skills ?? []),
      ].map((s) => s.toLowerCase())
    );

    let score = 40;
    const reasons: string[] = [];

    // Title relevance
    const roleTokens = role.split(/\s+/).filter((t) => t.length > 2);
    const titleHits = roleTokens.filter((t) => title.includes(t)).length;
    if (roleTokens.length && titleHits / roleTokens.length >= 0.6) {
      score += 22;
      reasons.push("Excellent title match");
    } else if (titleHits > 0 || roleTokens.some((t) => desc.includes(t))) {
      score += 12;
      reasons.push("Good title relevance");
    } else {
      score += 2;
    }

    // Skills match
    const required = job.skills.length
      ? job.skills
      : extractSkillsFromText(`${job.title} ${job.description}`);
    const matched = required.filter((s) => userSkills.has(s.toLowerCase()));
    const missing = required.filter((s) => !userSkills.has(s.toLowerCase()));
    if (userSkills.size > 0) {
      const ratio = matched.length / Math.max(required.length, 1);
      score += Math.round(ratio * 18);
      if (ratio >= 0.5) reasons.push("Strong skills overlap");
      else if (missing.length) reasons.push("Some skill gaps");
    } else {
      score += 8;
    }

    // Location match
    if (
      !location ||
      location === "anywhere" ||
      job.location.toLowerCase().includes(location) ||
      (location.includes("remote") && job.workMode === "remote")
    ) {
      score += 10;
      reasons.push(
        job.workMode === "remote" ? "Remote-friendly" : "Location match"
      );
    } else if (job.workMode === "remote" && criteria.workMode === "remote") {
      score += 10;
      reasons.push("Remote preference met");
    } else {
      score -= 4;
    }

    // Company reputation
    if (REPUTABLE.has(job.company.toLowerCase())) {
      score += 8;
      reasons.push("Strong company");
    } else {
      score += 2;
    }

    // Salary
    if (job.salaryMin || job.salaryMax) {
      score += 6;
      if (criteria.salaryMin && (job.salaryMax ?? 0) >= criteria.salaryMin) {
        score += 4;
        reasons.push("Meets salary target");
      }
    }

    // Recency
    if (job.postedAt) {
      const days =
        (Date.now() - new Date(job.postedAt).getTime()) / (1000 * 60 * 60 * 24);
      if (days <= 3) {
        score += 8;
        reasons.push("Recently posted");
      } else if (days <= 14) score += 4;
      else if (days > 45) score -= 4;
    }

    // Remote preference / employment type
    if (criteria.workMode && criteria.workMode !== "any") {
      if (job.workMode === criteria.workMode) score += 6;
      else score -= 3;
    }
    if (
      criteria.employmentType &&
      criteria.employmentType !== "any" &&
      job.employmentType === criteria.employmentType
    ) {
      score += 4;
    }

    score = clamp(Math.round(score), 1, 99);

    const summary = buildThreeLineSummary(job);
    const difficulty = estimateDifficulty(job, score);

    return {
      score,
      reason:
        reasons.slice(0, 3).join(", ") + (reasons.length ? "." : "Solid overall fit."),
      summary,
      requiredSkills: required.slice(0, 8),
      missingSkills: missing.slice(0, 6),
      resumeTips: buildResumeTips(job, missing, matched),
      interviewDifficulty: difficulty,
    };
  }
}

function buildThreeLineSummary(job: NormalizedJob): string {
  const line1 = `${job.title} at ${job.company} — ${job.location}.`;
  const line2 = job.salary
    ? `Compensation around ${job.salary}; ${job.employmentType} · ${job.workMode}.`
    : `${job.employmentType} role · ${job.workMode} work mode.`;
  const line3 = job.description
    ? job.description.slice(0, 160).replace(/\s+/g, " ").trim() +
      (job.description.length > 160 ? "…" : "")
    : `Focus areas: ${(job.skills.slice(0, 4).join(", ") || "general product engineering")}.`;
  return `${line1}\n${line2}\n${line3}`;
}

function buildResumeTips(
  job: NormalizedJob,
  missing: string[],
  matched: string[]
): string[] {
  const tips: string[] = [];
  if (matched.length) {
    tips.push(
      `Lead with impact stories involving ${matched.slice(0, 3).join(", ")}.`
    );
  } else {
    tips.push(`Mirror keywords from the ${job.title} posting in your summary.`);
  }
  if (missing.length) {
    tips.push(
      `Call out adjacent experience or coursework for ${missing.slice(0, 3).join(", ")}.`
    );
  } else {
    tips.push("Quantify outcomes (latency, revenue, users) in 2–3 bullets.");
  }
  tips.push(
    `Tailor your headline toward ${job.company}'s ${job.workMode} ${job.employmentType} opening.`
  );
  return tips.slice(0, 3);
}

function estimateDifficulty(
  job: NormalizedJob,
  score: number
): AiEnrichment["interviewDifficulty"] {
  const seniorish = /senior|staff|principal|lead|staff/i.test(job.title);
  if (seniorish && score < 70) return "very-hard";
  if (seniorish) return "hard";
  if (/junior|entry|intern/i.test(job.title)) return "easy";
  if (score >= 85) return "moderate";
  return "moderate";
}

export function polishParsedCriteria(
  parsed: Partial<SearchCriteria>,
  originalQuery?: string
): Partial<SearchCriteria> {
  const next = { ...parsed };
  let role = (next.role || "").trim();
  if (/^(python|react|java|golang|typescript|javascript|kotlin|rust|go)$/i.test(role)) {
    const label = role.toLowerCase() === "go" || role.toLowerCase() === "golang"
      ? "Go"
      : role[0].toUpperCase() + role.slice(1);
    role = `${label} Developer`;
  }
  if (!role) role = "Software Engineer";
  next.role = role;

  if ((!next.skills || next.skills.length === 0) && originalQuery) {
    const skills: string[] = [];
    for (const skill of ["Python", "TypeScript", "JavaScript", "React", "Java", "Go", "Kotlin", "Rust", "Node"]) {
      if (new RegExp(`\\b${skill}\\b`, "i").test(originalQuery)) skills.push(skill === "Node" ? "Node.js" : skill);
    }
    if (skills.length) next.skills = skills;
  }

  if (!next.location && originalQuery && /\beurope\b/i.test(originalQuery)) {
    next.location = "Europe";
  }
  if (!next.workMode && originalQuery && /\bremote\b/i.test(originalQuery)) {
    next.workMode = "remote";
  }

  return next;
}

export function heuristicParseNaturalLanguage(
  query: string
): Partial<SearchCriteria> {
  const q = query.trim();
  const lower = q.toLowerCase();

  let workMode: SearchCriteria["workMode"];
  if (/\bremote\b/.test(lower)) workMode = "remote";
  else if (/\bhybrid\b/.test(lower)) workMode = "hybrid";
  else if (/\bonsite\b|\bon-site\b/.test(lower)) workMode = "onsite";

  let employmentType: SearchCriteria["employmentType"];
  if (/\bpart[- ]?time\b/.test(lower)) employmentType = "part-time";
  else if (/\bcontract\b|\bfreelance\b/.test(lower)) employmentType = "contract";
  else if (/\bintern(ship)?\b/.test(lower)) employmentType = "internship";
  else if (/\bfull[- ]?time\b/.test(lower)) employmentType = "full-time";

  let experienceLevel: SearchCriteria["experienceLevel"];
  if (/\bintern\b/.test(lower)) experienceLevel = "internship";
  else if (/\bjunior\b|\bentry\b/.test(lower)) experienceLevel = "entry";
  else if (/\bsenior\b|\bsr\b/.test(lower)) experienceLevel = "senior";
  else if (/\bstaff\b|\blead\b|\bprincipal\b/.test(lower)) experienceLevel = "lead";
  else if (/\bmid[- ]?level\b|\bmid\b/.test(lower)) experienceLevel = "mid";

  const salaryMatch = lower.match(
    /(?:over|above|paying(?: over)?|salary(?: above)?|>|>=)\s*(?:€|eur|£|gbp|\$|usd|₹|inr)?\s*(\d+(?:[.,]\d+)?)\s*(k)?/i
  );
  let salaryMin: number | undefined;
  if (salaryMatch) {
    salaryMin = Number(salaryMatch[1].replace(",", ""));
    if (salaryMatch[2]) salaryMin *= 1000;
  }

  const skills: string[] = [];
  for (const skill of [
    "python",
    "typescript",
    "javascript",
    "react",
    "java",
    "golang",
    "go",
    "kotlin",
    "rust",
    "node",
  ]) {
    if (lower.includes(skill)) {
      skills.push(skill === "golang" ? "Go" : skill[0].toUpperCase() + skill.slice(1));
    }
  }

  let location = "";
  const locMatch = q.match(
    /\bin\s+([A-Za-z][A-Za-z\s\-]+?)(?:\s+paying|\s+over|\s+with|\s*$)/i
  );
  if (locMatch) location = locMatch[1].trim();
  else if (/\beurope\b/i.test(q)) location = "Europe";
  else if (/\bbangalore\b|\bbengaluru\b/i.test(q)) location = "Bangalore";
  else if (/\blondon\b/i.test(q)) location = "London";
  else if (workMode === "remote") location = "Remote";

  let role = q
    .replace(/\bremote\b/gi, " ")
    .replace(/\bhybrid\b/gi, " ")
    .replace(/\bonsite\b|\bon-site\b/gi, " ")
    .replace(/\bin\s+[A-Za-z][A-Za-z\s\-]*/gi, " ")
    .replace(/\bpaying\b.*$/gi, " ")
    .replace(/\bover\b.*$/gi, " ")
    .replace(/(?:€|eur|£|gbp|\$|usd|₹|inr)\s*\d[\d.,]*\s*k?/gi, " ")
    .replace(/\b\d+\s*k\b/gi, " ")
    .replace(/\bjobs?\b/gi, " ")
    .replace(/\s+/g, " ")
    .trim();

  if (!role || role.length < 3) {
    if (skills.some((s) => s.toLowerCase() === "python")) role = "Python Developer";
    else if (skills.some((s) => s.toLowerCase() === "react")) role = "React Developer";
    else role = "Software Engineer";
  } else if (/^(python|react|java|golang|typescript|javascript|kotlin|rust|go)$/i.test(role)) {
    role = `${role[0].toUpperCase()}${role.slice(1)} Developer`;
  }

  return {
    role,
    location: location || "Remote",
    workMode,
    employmentType,
    experienceLevel,
    salaryMin,
    skills: skills.length ? skills : undefined,
    naturalLanguage: query,
  };
}

export const aiRankingService = new AiRankingService();
