export interface AppEnvConfig {
  readonly apiBaseUrl: string;
  readonly appName: string;
  readonly healthPollIntervalMs: number;
}

const DEFAULT_API_BASE_URL = "http://localhost:8000";
const DEFAULT_APP_NAME = "Enterprise Intelligence Platform";
const DEFAULT_POLL_INTERVAL_MS = 30000;

function normalizeBaseUrl(rawUrl: string | undefined): string {
  const trimmed = rawUrl?.trim();
  if (!trimmed) {
    return DEFAULT_API_BASE_URL;
  }
  return trimmed.replace(/\/+$/, "");
}

function parsePositiveInt(rawValue: string | undefined, fallback: number): number {
  if (!rawValue) {
    return fallback;
  }
  const parsed = Number.parseInt(rawValue, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export const env: AppEnvConfig = {
  apiBaseUrl: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL),
  appName: import.meta.env.VITE_APP_NAME?.trim() || DEFAULT_APP_NAME,
  healthPollIntervalMs: parsePositiveInt(
    import.meta.env.VITE_HEALTH_POLL_INTERVAL_MS,
    DEFAULT_POLL_INTERVAL_MS,
  ),
};
