import { ApiError } from "./errors";
import type { ApiResponse } from "@/types";

export { ApiError, getErrorMessage } from "./errors";

const DEFAULT_BASE_URL = "http://localhost:5001/api";

// The base URL already ends in "/api"; callers pass paths such as "/api/boards".
// Strip the duplicate prefix so requests go to ".../api/boards", not ".../api/api/boards".
const baseUrl = () =>
  (
    (typeof window === "undefined"
      ? process.env.API_BASE_URL
      : process.env.NEXT_PUBLIC_API_BASE_URL) || DEFAULT_BASE_URL
  ).replace(/\/+$/, "");

const buildUrl = (path: string) => {
  const base = baseUrl();
  const rel = base.endsWith("/api") ? path.replace(/^\/api(?=\/|\?|$)/, "") : path;
  return `${base}${rel}`;
};

export async function apiClient<T>(
  path: string,
  token?: string | null,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(buildUrl(path), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(
      res.status,
      typeof body?.error === "string" ? body.error : "Request failed",
    );
  }
  return (body as ApiResponse<T>).data;
}
