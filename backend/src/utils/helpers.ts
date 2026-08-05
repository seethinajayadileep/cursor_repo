import crypto from "crypto";
import type { SearchCriteria } from "../types/index.js";

export function createId(prefix = "id"): string {
  return `${prefix}_${crypto.randomBytes(8).toString("hex")}`;
}

export function hashCriteria(criteria: SearchCriteria): string {
  const payload = JSON.stringify({
    role: criteria.role?.trim().toLowerCase(),
    location: criteria.location?.trim().toLowerCase(),
    experienceLevel: criteria.experienceLevel ?? "any",
    employmentType: criteria.employmentType ?? "any",
    salaryMin: criteria.salaryMin ?? null,
    salaryMax: criteria.salaryMax ?? null,
    workMode: criteria.workMode ?? "any",
    companySize: criteria.companySize ?? "any",
    naturalLanguage: criteria.naturalLanguage?.trim().toLowerCase() ?? null,
    skills: (criteria.skills ?? []).map((s) => s.toLowerCase()).sort(),
  });
  return crypto.createHash("sha256").update(payload).digest("hex");
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function stripHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function parseSalaryNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value !== "string") return null;
  const cleaned = value.replace(/,/g, "").match(/(\d+(?:\.\d+)?)\s*([kK])?/);
  if (!cleaned) return null;
  let num = Number(cleaned[1]);
  if (cleaned[2]) num *= 1000;
  return Number.isFinite(num) ? num : null;
}

export function normalizeWorkMode(
  value?: string | null
): "remote" | "hybrid" | "onsite" | "unknown" {
  if (!value) return "unknown";
  const v = value.toLowerCase();
  if (v.includes("remote") || v.includes("work from home") || v === "wfh") {
    return "remote";
  }
  if (v.includes("hybrid")) return "hybrid";
  if (v.includes("onsite") || v.includes("on-site") || v.includes("office")) {
    return "onsite";
  }
  return "unknown";
}

export function normalizeEmploymentType(value?: string | null): string {
  if (!value) return "full-time";
  const v = value.toLowerCase();
  if (v.includes("part")) return "part-time";
  if (v.includes("contract") || v.includes("freelance")) return "contract";
  if (v.includes("temp")) return "temporary";
  if (v.includes("intern")) return "internship";
  return "full-time";
}
