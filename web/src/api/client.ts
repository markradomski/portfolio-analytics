/**
 * The one place an HTTP request is made. Components must never call fetch()
 * directly (sec 5) -- every screen goes through analytics.ts/portfolio.ts,
 * which go through this.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: string;
  path: string;

  constructor(status: number, detail: string, path: string) {
    super(`${status} ${detail} (${path})`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.path = path;
  }
}

export async function apiGet<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(path, BASE_URL);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) url.searchParams.set(key, String(value));
    }
  }

  const response = await fetch(url.toString());
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      /* body wasn't JSON; keep the status text */
    }
    throw new ApiError(response.status, detail, path);
  }
  return response.json() as Promise<T>;
}
