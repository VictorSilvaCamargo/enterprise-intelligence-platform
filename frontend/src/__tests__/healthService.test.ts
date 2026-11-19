import { afterEach, describe, expect, it, vi } from "vitest";
import { fetchLiveness, fetchReadiness } from "../services/healthService";
import { ApiClientError } from "../services/httpClient";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("healthService", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches liveness metadata from GET /health", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse({
        status: "ok",
        service: "Enterprise Intelligence Platform",
        version: "0.1.0",
        environment: "test",
        timestamp: "2026-11-19T12:00:00Z",
      }),
    );

    const result = await fetchLiveness();
    expect(result.status).toBe("ok");
    expect(result.version).toBe("0.1.0");
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://localhost:8000/health",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("parses degraded readiness payload on HTTP 503", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      jsonResponse(
        {
          status: "degraded",
          service: "Enterprise Intelligence Platform",
          version: "0.1.0",
          environment: "test",
          timestamp: "2026-11-19T12:00:00Z",
          dependencies: {
            postgresql: { status: "up", latency_ms: 1.8, detail: "Connected" },
            redis: { status: "down", latency_ms: 50.2, detail: "Connection failed (OSError)" },
          },
        },
        503,
      ),
    );

    const result = await fetchReadiness();
    expect(result.httpStatus).toBe(503);
    expect(result.data.status).toBe("degraded");
    expect(result.data.dependencies.redis.status).toBe("down");
  });

  it("throws ApiClientError with isNetworkError when backend is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new TypeError("Failed to fetch"));

    await expect(fetchLiveness()).rejects.toMatchObject({
      name: "ApiClientError",
      isNetworkError: true,
    } satisfies Partial<ApiClientError>);
  });
});
