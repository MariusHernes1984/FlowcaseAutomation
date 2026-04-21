import axios, { AxiosError } from "axios";

/**
 * Single axios instance used by every API module.
 *
 * - Sends cookies so the HttpOnly refresh cookie makes it to /auth/refresh.
 * - Attaches the in-memory access token on every request (set via setAccessToken).
 * - On 401 it tries one /auth/refresh then retries, so expired access tokens
 *   don't kick the user out mid-session.
 */
let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${accessToken}`;
  }
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshOnce(): Promise<string | null> {
  if (refreshing) return refreshing;
  refreshing = (async () => {
    try {
      const r = await axios.post("/api/auth/refresh", null, {
        withCredentials: true,
      });
      const token = r.data?.access_token ?? null;
      setAccessToken(token);
      return token;
    } catch {
      setAccessToken(null);
      return null;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

api.interceptors.response.use(
  (r) => r,
  async (err: AxiosError) => {
    const original = err.config as
      | (typeof err.config & { _retried?: boolean })
      | undefined;
    if (
      err.response?.status === 401 &&
      original &&
      !original._retried &&
      !original.url?.endsWith("/auth/refresh") &&
      !original.url?.endsWith("/auth/login")
    ) {
      original._retried = true;
      const newToken = await refreshOnce();
      if (newToken) {
        original.headers = original.headers ?? {};
        (original.headers as Record<string, string>).Authorization =
          `Bearer ${newToken}`;
        return api.request(original);
      }
    }
    return Promise.reject(err);
  },
);
