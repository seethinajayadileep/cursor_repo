export interface PortalUser {
  id: string;
  email: string;
  name: string;
  passwordHash: string;
  createdAt: string;
}

export type SkillsMode = "auto" | "manual";

export interface PortalPrefs {
  userId: string;
  /** Primary role (kept for compatibility) */
  role: string;
  /** Multiple roles to search daily */
  roles: string[];
  location: string;
  experienceLevel: string;
  employmentType: string;
  workMode: string;
  companySize: string;
  salaryMin?: number;
  salaryMax?: number;
  /** auto = use resume skills; manual = use manualSkills */
  skillsMode: SkillsMode;
  manualSkills: string[];
  alertsEnabled: boolean;
  topN: number;
  updatedAt: string;
}

export interface TelegramLink {
  userId: string;
  chatId: string;
  username?: string | null;
  linkToken?: string | null;
  linkedAt: string | null;
}

export interface AlertRun {
  id: string;
  userId: string;
  ranAt: string;
  status: "success" | "skipped" | "error";
  jobsSent: number;
  message?: string;
  preview?: Array<{
    title: string;
    company: string;
    score: number;
    applyUrl?: string | null;
  }>;
}
