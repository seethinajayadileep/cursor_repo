import { z } from "zod";

export const searchBodySchema = z.object({
  role: z.string().min(1).max(120).optional(),
  location: z.string().max(120).optional().default(""),
  experienceLevel: z
    .enum(["internship", "entry", "mid", "senior", "lead", "executive", "any"])
    .optional()
    .default("any"),
  employmentType: z
    .enum(["full-time", "part-time", "contract", "temporary", "internship", "any"])
    .optional()
    .default("any"),
  salaryMin: z.number().nonnegative().optional(),
  salaryMax: z.number().nonnegative().optional(),
  workMode: z.enum(["remote", "hybrid", "onsite", "any"]).optional().default("any"),
  companySize: z
    .enum(["startup", "small", "medium", "large", "enterprise", "any"])
    .optional()
    .default("any"),
  naturalLanguage: z.string().max(500).optional(),
  skills: z.array(z.string()).optional(),
  forceRefresh: z.boolean().optional(),
  page: z.number().int().positive().optional(),
  pageSize: z.number().int().positive().max(50).optional(),
  sort: z.enum(["score", "salary", "date", "company", "title"]).optional(),
  userId: z.string().max(80).optional(),
});

export const nlSearchSchema = z.object({
  query: z.string().min(3).max(500),
  userId: z.string().max(80).optional(),
  forceRefresh: z.boolean().optional(),
});

export const bookmarkSchema = z.object({
  userId: z.string().min(1).max(80).default("anonymous"),
  job: z.record(z.unknown()),
});

export const alertSchema = z.object({
  userId: z.string().min(1).max(80).default("anonymous"),
  email: z.string().email(),
  criteria: z.record(z.unknown()),
});
