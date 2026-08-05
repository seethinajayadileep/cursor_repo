import type { SearchCriteria } from "@/types";

const API_URL = (() => {
  const raw = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000")
    .trim()
    .replace(/\/+$/, "");
  if (!raw) return "http://localhost:4000";
  if (/^https?:\/\//i.test(raw)) return raw;
  return `https://${raw}`;
})();

const TOKEN_KEY = "scout_portal_token";

export function getPortalToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setPortalToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function portalRequest<T>(
  path: string,
  init?: RequestInit & { auth?: boolean }
): Promise<T> {
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string>),
  };
  if (!(init?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  if (init?.auth !== false) {
    const token = getPortalToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}/api/portal${path}`, {
    ...init,
    headers,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || "Request failed");
  }
  return res.json() as Promise<T>;
}

export interface PortalMe {
  user: { id: string; email: string; name: string; createdAt: string };
  prefs: {
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
  };
  resume: { skills: string[]; updatedAt: string; characters: number } | null;
  telegram: {
    linked: boolean;
    chatId: string | null;
    username: string | null;
    linkedAt: string | null;
    botConfigured: boolean;
    botUsername: string | null;
  };
  recentRuns: Array<{
    id: string;
    ranAt: string;
    status: string;
    jobsSent: number;
    message?: string;
    preview?: Array<{ title: string; company: string; score: number }>;
  }>;
  schedule: { cron: string; timezone: string };
}

export const portalApi = {
  register: (body: { email: string; password: string; name?: string }) =>
    portalRequest<{ user: PortalMe["user"]; token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify(body),
      auth: false,
    }),

  login: (body: { email: string; password: string }) =>
    portalRequest<{ user: PortalMe["user"]; token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify(body),
      auth: false,
    }),

  me: () => portalRequest<PortalMe>("/me"),

  savePrefs: (prefs: PortalMe["prefs"]) =>
    portalRequest<{ prefs: PortalMe["prefs"] }>("/prefs", {
      method: "PUT",
      body: JSON.stringify(prefs),
    }),

  uploadResume: async (file?: File, text?: string) => {
    const form = new FormData();
    if (text) form.append("text", text);
    if (file) form.append("resume", file);
    return portalRequest<{
      skills: string[];
      message: string;
      source: string;
    }>("/resume", { method: "POST", body: form });
  },

  linkTelegram: () =>
    portalRequest<{
      token: string;
      deepLink: string | null;
      instructions: string;
      botConfigured: boolean;
    }>("/telegram/link", { method: "POST" }),

  unlinkTelegram: () =>
    portalRequest<{ ok: boolean }>("/telegram/unlink", { method: "POST" }),

  runDigest: () =>
    portalRequest<{ ok: boolean; latest: PortalMe["recentRuns"][0] | null }>(
      "/digest/run",
      { method: "POST" }
    ),

  history: () =>
    portalRequest<{ runs: PortalMe["recentRuns"] }>("/digest/history"),
};

export type { SearchCriteria };
