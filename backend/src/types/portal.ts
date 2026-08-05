export interface PortalUser {
  id: string;
  email: string;
  name: string;
  passwordHash: string;
  createdAt: string;
}

export interface PortalPrefs {
  userId: string;
  role: string;
  location: string;
  experienceLevel: string;
  employmentType: string;
  workMode: string;
  companySize: string;
  salaryMin?: number;
  salaryMax?: number;
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
  preview?: Array<{ title: string; company: string; score: number; applyUrl?: string | null }>;
}
