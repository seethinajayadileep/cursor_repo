export type ExperienceLevel =
  | "internship"
  | "entry"
  | "mid"
  | "senior"
  | "lead"
  | "executive"
  | "any";

export type EmploymentType =
  | "full-time"
  | "part-time"
  | "contract"
  | "temporary"
  | "internship"
  | "any";

export type WorkMode = "remote" | "hybrid" | "onsite" | "any";

export type CompanySize =
  | "startup"
  | "small"
  | "medium"
  | "large"
  | "enterprise"
  | "any";

export type SortOption =
  | "score"
  | "salary"
  | "date"
  | "company"
  | "title";

export interface SalaryRange {
  min?: number;
  max?: number;
  currency?: string;
}

export interface SearchFilters {
  experienceLevel?: ExperienceLevel;
  employmentType?: EmploymentType;
  salaryMin?: number;
  salaryMax?: number;
  workMode?: WorkMode;
  companySize?: CompanySize;
}

export interface SearchCriteria extends SearchFilters {
  role: string;
  location: string;
  naturalLanguage?: string;
  skills?: string[];
  userId?: string;
}

export interface RawJob {
  id?: string;
  title?: string;
  company?: string;
  companyName?: string;
  location?: string;
  salary?: string | number | null;
  salaryMin?: number | null;
  salaryMax?: number | null;
  currency?: string | null;
  employmentType?: string | null;
  jobType?: string | null;
  workMode?: string | null;
  workplaceType?: string | null;
  description?: string | null;
  descriptionHtml?: string | null;
  postedAt?: string | null;
  postedDate?: string | null;
  publishedAt?: string | null;
  url?: string | null;
  applyUrl?: string | null;
  link?: string | null;
  companyLogo?: string | null;
  companySize?: string | null;
  skills?: string[] | null;
  experienceLevel?: string | null;
  [key: string]: unknown;
}

export interface NormalizedJob {
  id: string;
  title: string;
  company: string;
  location: string;
  salary: string | null;
  salaryMin: number | null;
  salaryMax: number | null;
  currency: string | null;
  employmentType: string;
  workMode: WorkMode | "unknown";
  description: string;
  postedAt: string | null;
  applyUrl: string | null;
  companyLogo: string | null;
  companySize: string | null;
  skills: string[];
  experienceLevel: string | null;
  source: string;
}

export interface AiEnrichment {
  score: number;
  reason: string;
  summary: string;
  requiredSkills: string[];
  missingSkills: string[];
  resumeTips: string[];
  interviewDifficulty: "easy" | "moderate" | "hard" | "very-hard";
}

export interface RankedJob extends NormalizedJob, AiEnrichment {}

export interface SearchProgress {
  stage:
    | "queued"
    | "scraping"
    | "cleaning"
    | "ranking"
    | "complete"
    | "error";
  message: string;
  percent: number;
  runId?: string;
}

export interface SearchResult {
  searchId: string;
  criteria: SearchCriteria;
  jobs: RankedJob[];
  total: number;
  cached: boolean;
  createdAt: string;
  mode: "live" | "demo";
  progress?: SearchProgress;
}

export interface SavedSearch {
  id: string;
  userId: string;
  criteria: SearchCriteria;
  createdAt: string;
  alertEmail?: string | null;
}

export interface BookmarkedJob {
  id: string;
  userId: string;
  job: RankedJob;
  savedAt: string;
}

export interface SalaryInsight {
  currency: string;
  min: number;
  max: number;
  median: number;
  average: number;
  sampleSize: number;
  byWorkMode: Record<string, { average: number; count: number }>;
  byCompany: Array<{ company: string; average: number; count: number }>;
}

export interface CompanyTrend {
  company: string;
  openings: number;
  averageScore: number;
  remoteShare: number;
  topRoles: string[];
}

export interface ResumeProfile {
  text: string;
  skills: string[];
  yearsExperience?: number;
  preferredRoles?: string[];
}
