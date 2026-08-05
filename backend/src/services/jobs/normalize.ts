import crypto from "crypto";
import type { NormalizedJob, RawJob } from "../../types/index.js";
import {
  createId,
  normalizeEmploymentType,
  normalizeWorkMode,
  parseSalaryNumber,
  stripHtml,
} from "../../utils/helpers.js";

export function normalizeJob(raw: RawJob, source = "apify"): NormalizedJob {
  const title = String(raw.title ?? "Untitled role").trim();
  const company = String(raw.company ?? raw.companyName ?? "Unknown company").trim();
  const location = String(raw.location ?? "Not specified").trim();
  const descriptionRaw = String(
    raw.description ?? raw.descriptionHtml ?? ""
  );
  const description = stripHtml(descriptionRaw).slice(0, 4000);

  const salaryMin =
    typeof raw.salaryMin === "number"
      ? raw.salaryMin
      : parseSalaryNumber(raw.salary);
  const salaryMax =
    typeof raw.salaryMax === "number"
      ? raw.salaryMax
      : parseSalaryMax(raw.salary) ?? salaryMin;

  const salary =
    typeof raw.salary === "string" && raw.salary.trim()
      ? raw.salary.trim()
      : formatSalary(salaryMin, salaryMax, raw.currency);

  const skills = Array.isArray(raw.skills)
    ? raw.skills.map(String).filter(Boolean)
    : extractSkillsFromText(`${title} ${description}`);

  const applyUrl =
    (raw.applyUrl || raw.url || raw.link || null)?.toString() ?? null;

  const postedAt =
    (raw.postedAt || raw.postedDate || raw.publishedAt || null)?.toString() ??
    null;

  const fingerprint = crypto
    .createHash("md5")
    .update(`${title}|${company}|${location}`.toLowerCase())
    .digest("hex");

  return {
    id: raw.id?.toString() || createId(`job_${fingerprint.slice(0, 8)}`),
    title,
    company,
    location,
    salary,
    salaryMin: salaryMin ?? null,
    salaryMax: salaryMax ?? null,
    currency: raw.currency?.toString() ?? null,
    employmentType: normalizeEmploymentType(
      (raw.employmentType || raw.jobType)?.toString()
    ),
    workMode: normalizeWorkMode(
      (raw.workMode || raw.workplaceType || location)?.toString()
    ),
    description,
    postedAt,
    applyUrl,
    companyLogo: raw.companyLogo?.toString() ?? null,
    companySize: raw.companySize?.toString() ?? null,
    skills,
    experienceLevel: raw.experienceLevel?.toString() ?? null,
    source,
  };
}

export function cleanAndDeduplicate(rawJobs: RawJob[]): NormalizedJob[] {
  const seen = new Set<string>();
  const normalized: NormalizedJob[] = [];

  for (const raw of rawJobs) {
    const job = normalizeJob(raw);
    if (!job.title || job.title === "Untitled role") continue;
    if (!job.company || job.company === "Unknown company") continue;

    const key = `${job.title}|${job.company}|${job.location}`
      .toLowerCase()
      .replace(/\s+/g, " ");
    if (seen.has(key)) continue;
    seen.add(key);
    normalized.push(job);
  }

  return normalized;
}

function parseSalaryMax(value: unknown): number | null {
  if (typeof value !== "string") return null;
  const matches = [...value.replace(/,/g, "").matchAll(/(\d+(?:\.\d+)?)\s*([kK])?/g)];
  if (matches.length < 2) return parseSalaryNumber(value);
  const last = matches[matches.length - 1];
  let num = Number(last[1]);
  if (last[2]) num *= 1000;
  return Number.isFinite(num) ? num : null;
}

function formatSalary(
  min: number | null | undefined,
  max: number | null | undefined,
  currency?: string | null
): string | null {
  if (!min && !max) return null;
  const cur = currency ?? "USD";
  if (min && max && min !== max) {
    return `${cur} ${Math.round(min).toLocaleString()} – ${Math.round(max).toLocaleString()}`;
  }
  const val = min ?? max;
  return val ? `${cur} ${Math.round(val).toLocaleString()}` : null;
}

const SKILL_LEXICON = [
  "TypeScript",
  "JavaScript",
  "Python",
  "Java",
  "Kotlin",
  "Go",
  "Rust",
  "React",
  "Next.js",
  "Node.js",
  "Vue",
  "Angular",
  "PostgreSQL",
  "MySQL",
  "MongoDB",
  "Redis",
  "Kafka",
  "AWS",
  "GCP",
  "Azure",
  "Kubernetes",
  "Docker",
  "Terraform",
  "GraphQL",
  "REST",
  "Swift",
  "SwiftUI",
  "PyTorch",
  "JAX",
  "TensorFlow",
  "SQL",
  "Figma",
  "CI/CD",
  "Linux",
  "FastAPI",
  "Spring",
  "Microservices",
  "Distributed Systems",
  "Machine Learning",
  "MLOps",
];

export function extractSkillsFromText(text: string): string[] {
  const lower = text.toLowerCase();
  return SKILL_LEXICON.filter((skill) =>
    lower.includes(skill.toLowerCase())
  ).slice(0, 12);
}
