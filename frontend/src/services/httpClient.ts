import { env } from "../config/env";
import type { HttpResponse } from "../types/api";

const DEFAULT_TIMEOUT_MS = 8000;

export class ApiClientError extends Error {
  readonly status: number;
  readonly payload: unknown;
  readonly isNetworkError: boolean;

  constructor(
    message: string,
    options: { status?: number; payload?: unknown; isNetworkError?: boolean } = {},
  ) {
    super(message);
    this.name = "ApiClientError";
    this.status = options.status ?? 0;
    this.payload = options.payload ?? null;
    this.isNetworkError = options.isNetworkError ?? false;
  }
}

export interface RequestOptions {
  signal?: AbortSignal;
  timeoutMs?: number;
  acceptStatuses?: number[];
}

function buildRequestSignal(
  externalSignal: AbortSignal | undefined,
  timeoutMs: number,
): { signal: AbortSignal; cleanup: () => void } {
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => controller.abort(), timeoutMs);

  const onExternalAbort = () => controller.abort();
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener("abort", onExternalAbort, { once: true });
    }
  }

  return {
    signal: controller.signal,
    cleanup: () => {
      globalThis.clearTimeout(timeoutId);
      externalSignal?.removeEventListener("abort", onExternalAbort);
    },
  };
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "message" in payload &&
    typeof (payload as { message?: unknown }).message === "string"
  ) {
    const msg = (payload as { message: string }).message.trim();
    if (msg) {
      return msg;
    }
  }
  return fallback;
}

export function buildQueryString(
  params: Record<string, string | number | boolean | undefined | null>,
): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      searchParams.set(key, String(value));
    }
  }
  const encoded = searchParams.toString();
  return encoded ? `?${encoded}` : "";
}

async function performRequest<T>(
  path: string,
  init: Omit<RequestInit, "signal">,
  options: RequestOptions = {},
): Promise<HttpResponse<T>> {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = `${env.apiBaseUrl}${normalizedPath}`;
  const { signal, cleanup } = buildRequestSignal(
    options.signal,
    options.timeoutMs ?? DEFAULT_TIMEOUT_MS,
  );

  try {
    const response = await fetch(url, {
      ...init,
      signal,
    });

    const contentType = response.headers.get("content-type") ?? "";
    const isJson = contentType.includes("application/json");
    const parsedBody: unknown = isJson ? await response.json() : await response.text();
    const isAccepted = response.ok || (options.acceptStatuses?.includes(response.status) ?? false);

    if (!isAccepted || !isJson) {
      const fallback = `Request to ${normalizedPath} failed with status ${response.status}`;
      throw new ApiClientError(extractErrorMessage(parsedBody, fallback), {
        status: response.status,
        payload: parsedBody,
      });
    }

    return {
      status: response.status,
      data: parsedBody as T,
      requestId: response.headers.get("x-request-id"),
    };
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }
    const message =
      error instanceof Error && error.name === "AbortError"
        ? "Backend request timed out or was cancelled."
        : "Unable to reach the backend API service.";
    throw new ApiClientError(message, { isNetworkError: true });
  } finally {
    cleanup();
  }
}

export async function requestJson<T>(
  path: string,
  options: RequestOptions = {},
): Promise<HttpResponse<T>> {
  return performRequest<T>(
    path,
    {
      method: "GET",
      headers: { Accept: "application/json" },
    },
    options,
  );
}

export async function requestPostFormData<T>(
  path: string,
  formData: FormData,
  options: RequestOptions = {},
): Promise<HttpResponse<T>> {
  return performRequest<T>(
    path,
    {
      method: "POST",
      headers: { Accept: "application/json" },
      body: formData,
    },
    { timeoutMs: 30000, ...options },
  );
}
