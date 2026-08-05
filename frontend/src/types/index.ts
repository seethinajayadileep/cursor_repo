export type WorkMode = "remote" | "hybrid" | "onsite" | "any" | "unknown";

export interface SearchCriteria {
  role: string;
  location: string;
  experienceLevel?: string;
  employmentType?: string;
  salaryMin?: number;
  salaryMax?: number;
  workMode?: string;
  companySize?: string;
  naturalLanguage?: string;
  skills?: string[];
}

export interface RankedJob {
  id: string;
  title: string;
  company: string;
  location: string;
  salary: string | null;
  salaryMin: number | null;
  salaryMax: number | null;
  currency: string | null;
  employmentType: string;
  workMode: WorkMode;
  description: string;
  postedAt: string | null;
  applyUrl: string | null;
  linkedinUrl?: string | null;
  isExternalApply?: boolean;
  companyLogo: string | null;
  companySize: string | null;
  skills: string[];
  experienceLevel: string | null;
  source: string;
  score: number;
  reason: string;
  summary: string;
  requiredSkills: string[];
  missingSkills: string[];
  resumeTips: string[];
  interviewDifficulty: "easy" | "moderate" | "hard" | "very-hard";
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

export interface SearchResponse {
  searchId: string;
  criteria: SearchCriteria;
  jobs: RankedJob[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
  cached: boolean;
  createdAt: string;
  mode: "live" | "demo";
  insights?: {
    salary: SalaryInsight | null;
    companies: CompanyTrend[];
  };
}

export interface BookmarkedJob {
  id: string;
  userId: string;
  job: RankedJob;
  savedAt: string;
}

export interface HealthResponse {
  ok: boolean;
  services: {
    apify: string;
    ai: string;
    cache: string;
    database: string;
  };
}
