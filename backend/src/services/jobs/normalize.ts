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
  const company = String(
    raw.company ?? raw.companyName ?? "Unknown company"
  ).trim();
  const location = String(
    typeof raw.location === "object" && raw.location
      ? (raw.location as { defaultLocalizedName?: string; abbreviatedLocalizedName?: string })
          .defaultLocalizedName ||
          (raw.location as { abbreviatedLocalizedName?: string })
            .abbreviatedLocalizedName ||
          "Not specified"
      : raw.location ?? "Not specified"
  ).trim();

  const descriptionRaw = String(
    raw.descriptionText ?? raw.description ?? raw.descriptionHtml ?? ""
  );
  const description = stripHtml(descriptionRaw).slice(0, 4000);

  const salaryParsed = parseSalaryFields(raw);
  const salaryMin = salaryParsed.min;
  const salaryMax = salaryParsed.max;
  const currency = salaryParsed.currency ?? raw.currency?.toString() ?? null;

  const salary =
    typeof raw.salary === "string" && raw.salary.trim()
      ? raw.salary.trim()
      : salaryParsed.label || formatSalary(salaryMin, salaryMax, currency);

  const skills = Array.isArray(raw.skills)
    ? raw.skills.map(String).filter(Boolean)
    : extractSkillsFromText(`${title}\n${description}`);

  const { applyUrl, linkedinUrl, isExternalApply } = resolveApplyLinks(raw);

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
    currency,
    employmentType: normalizeEmploymentType(
      (
        raw.employmentType ||
        raw.jobType ||
        raw.contractType ||
        (Array.isArray(raw.benefits) ? raw.benefits.join(" ") : "")
      )?.toString()
    ),
    workMode: resolveWorkMode(raw, location, description),
    description,
    postedAt,
    applyUrl,
    linkedinUrl,
    isExternalApply,
    companyLogo: raw.companyLogo?.toString() ?? null,
    companySize: raw.companySize?.toString() ?? null,
    skills,
    experienceLevel: raw.experienceLevel?.toString() ?? null,
    source,
  };
}

function resolveWorkMode(
  raw: RawJob,
  location: string,
  description: string
): ReturnType<typeof normalizeWorkMode> {
  const benefits = Array.isArray(raw.benefits)
    ? raw.benefits.map(String).join(" ")
    : String(raw.benefits ?? "");
  const blob = [
    raw.workMode,
    raw.workplaceType,
    raw.workType,
    raw.workplace,
    raw.remote,
    benefits,
    location,
    description.slice(0, 500),
  ]
    .filter(Boolean)
    .join(" ");

  return normalizeWorkMode(blob);
}

function parseSalaryFields(raw: RawJob): {
  min: number | null;
  max: number | null;
  currency: string | null;
  label: string | null;
} {
  if (typeof raw.salaryMin === "number" || typeof raw.salaryMax === "number") {
    return {
      min: typeof raw.salaryMin === "number" ? raw.salaryMin : null,
      max: typeof raw.salaryMax === "number" ? raw.salaryMax : null,
      currency: raw.currency?.toString() ?? null,
      label: null,
    };
  }

  const info = raw.salaryInfo;
  if (Array.isArray(info) && info.length > 0) {
    const nums = info
      .map((v) => parseSalaryNumber(v))
      .filter((n): n is number => n !== null);
    const joined = info.map(String).join(" – ");
    const currency =
      detectCurrency(joined) ?? raw.currency?.toString() ?? null;
    return {
      min: nums[0] ?? null,
      max: nums[nums.length - 1] ?? nums[0] ?? null,
      currency,
      label: joined || null,
    };
  }

  if (typeof raw.salary === "string") {
    return {
      min: parseSalaryNumber(raw.salary),
      max: parseSalaryMax(raw.salary),
      currency: detectCurrency(raw.salary),
      label: raw.salary.trim() || null,
    };
  }

  return { min: null, max: null, currency: null, label: null };
}

function detectCurrency(text: string): string | null {
  if (/₹|inr/i.test(text)) return "INR";
  if (/€|eur/i.test(text)) return "EUR";
  if (/£|gbp/i.test(text)) return "GBP";
  if (/\$|usd/i.test(text)) return "USD";
  return null;
}

function isLinkedInUrl(url: string): boolean {
  try {
    const host = new URL(url).hostname.toLowerCase();
    return host.includes("linkedin.com");
  } catch {
    return /linkedin\.com/i.test(url);
  }
}

function asUrl(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  if (!trimmed || !/^https?:\/\//i.test(trimmed)) return null;
  return trimmed;
}

/** Prefer company/external apply links; keep LinkedIn as fallback. */
export function resolveApplyLinks(raw: RawJob): {
  applyUrl: string | null;
  linkedinUrl: string | null;
  isExternalApply: boolean;
} {
  const candidates = [
    raw.applyUrl,
    raw.externalApplyUrl,
    raw.applicationUrl,
    raw.companyApplyUrl,
    raw.jobApplyUrl,
    raw.applyLink,
    raw.url,
    raw.link,
  ]
    .map(asUrl)
    .filter((u): u is string => Boolean(u));

  const external = candidates.find((u) => !isLinkedInUrl(u)) ?? null;
  const linkedin =
    candidates.find((u) => isLinkedInUrl(u) && /\/jobs\//i.test(u)) ??
    candidates.find((u) => isLinkedInUrl(u)) ??
    null;

  if (external) {
    return {
      applyUrl: external,
      linkedinUrl: linkedin,
      isExternalApply: true,
    };
  }

  return {
    applyUrl: linkedin,
    linkedinUrl: linkedin,
    isExternalApply: false,
  };
}

export function cleanAndDeduplicate(
  rawJobs: RawJob[],
  source = "apify"
): NormalizedJob[] {
  const seen = new Set<string>();
  const normalized: NormalizedJob[] = [];

  for (const raw of rawJobs) {
    const job = normalizeJob(raw, source);
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
  const matches = [
    ...value.replace(/,/g, "").matchAll(/(\d+(?:\.\d+)?)\s*([kK])?/g),
  ];
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
  "Kotlin",
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
  "SwiftUI",
  "Swift",
  "PyTorch",
  "TensorFlow",
  "JAX",
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
  "Java",
  "Go",
];

export function extractSkillsFromText(text: string): string[] {
  const matches: string[] = [];
  for (const skill of SKILL_LEXICON) {
    if (skillMatches(text, skill)) matches.push(skill);
  }
  return matches.slice(0, 12);
}

function skillMatches(text: string, skill: string): boolean {
  const escaped = skill.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Word-boundary style match so "Go" != "ongoing", "Java" != "JavaScript"
  const pattern =
    skill.length <= 3
      ? new RegExp(`(?:^|[^A-Za-z])${escaped}(?:[^A-Za-z]|$)`, "i")
      : new RegExp(`(?:^|[^A-Za-z])${escaped}(?:[^A-Za-z]|$)`, "i");
  return pattern.test(text);
}
