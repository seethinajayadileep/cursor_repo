import type {
  BookmarkedJob,
  HealthResponse,
  RankedJob,
  SearchCriteria,
  SearchResponse,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

export function getUserId(): string {
  if (typeof window === "undefined") return "anonymous";
  const key = "scout_user_id";
  let id = localStorage.getItem(key);
  if (!id) {
    id = `user_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem(key, id);
  }
  return id;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(err.error || "Request failed");
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<HealthResponse>("/api/health"),

  search: (body: SearchCriteria & {
    page?: number;
    pageSize?: number;
    sort?: string;
    forceRefresh?: boolean;
    userId?: string;
  }) =>
    request<SearchResponse>("/api/search", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  naturalSearch: (query: string, userId?: string) =>
    request<SearchResponse>("/api/search/natural", {
      method: "POST",
      body: JSON.stringify({ query, userId }),
    }),

  getSearch: (
    searchId: string,
    params: Record<string, string | number | undefined>
  ) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return request<SearchResponse>(`/api/search/${searchId}?${qs}`);
  },

  listSearches: () =>
    request<{
      searches: Array<{
        searchId: string;
        criteria: SearchCriteria;
        total: number;
        createdAt: string;
        mode: string;
      }>;
    }>("/api/searches"),

  recommendations: () => request<{ jobs: RankedJob[] }>("/api/recommendations"),

  bookmarks: (userId: string) =>
    request<{ bookmarks: BookmarkedJob[] }>(`/api/bookmarks?userId=${userId}`),

  addBookmark: (userId: string, job: RankedJob) =>
    request<BookmarkedJob>("/api/bookmarks", {
      method: "POST",
      body: JSON.stringify({ userId, job }),
    }),

  removeBookmark: (userId: string, id: string) =>
    request<{ deleted: boolean }>(`/api/bookmarks/${id}?userId=${userId}`, {
      method: "DELETE",
    }),

  createAlert: (userId: string, email: string, criteria: SearchCriteria) =>
    request("/api/alerts", {
      method: "POST",
      body: JSON.stringify({ userId, email, criteria }),
    }),

  uploadResume: async (userId: string, file?: File, text?: string) => {
    const form = new FormData();
    form.append("userId", userId);
    if (text) form.append("text", text);
    if (file) form.append("resume", file);
    return request<{ skills: string[]; message: string }>("/api/resume", {
      method: "POST",
      body: form,
    });
  },

  exportCsvUrl: (searchId: string) => `${API_URL}/api/export/${searchId}.csv`,
  exportPdfUrl: (searchId: string) => `${API_URL}/api/export/${searchId}.pdf`,
};
