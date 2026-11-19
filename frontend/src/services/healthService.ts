import { requestJson } from "./httpClient";
import type { HealthResponse, ReadinessResponse } from "../types/health";

export async function fetchLiveness(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await requestJson<HealthResponse>("/health", { signal });
  return response.data;
}

export async function fetchReadiness(
  signal?: AbortSignal,
): Promise<{ httpStatus: number; data: ReadinessResponse }> {
  const response = await requestJson<ReadinessResponse>("/health/ready", {
    signal,
    // 503 returns a valid ReadinessResponse JSON body with status="degraded".
    acceptStatuses: [503],
  });
  return {
    httpStatus: response.status,
    data: response.data,
  };
}
