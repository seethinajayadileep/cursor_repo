async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(path, { ...options, headers });
  const text = await res.text();
  let data: unknown = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  if (!res.ok) {
    const err = (data as { error?: string })?.error || res.statusText || "Request failed";
    throw new Error(err);
  }
  return data as T;
}

export const api = {
  get: <T,>(path: string, token?: string | null) => request<T>(path, { method: "GET" }, token),
  post: <T,>(path: string, body?: unknown, token?: string | null) =>
    request<T>(
      path,
      {
        method: "POST",
        body: body instanceof FormData ? body : JSON.stringify(body ?? {}),
      },
      token
    ),
  put: <T,>(path: string, body?: unknown, token?: string | null) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(body ?? {}) }, token),
  patch: <T,>(path: string, body?: unknown, token?: string | null) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(body ?? {}) }, token),
  delete: <T,>(path: string, token?: string | null) => request<T>(path, { method: "DELETE" }, token),
};
