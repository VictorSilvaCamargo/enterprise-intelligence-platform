export type DependencyState = "up" | "down";

export interface DependencyStatus {
  status: DependencyState;
  latency_ms: number;
  detail: string;
}

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
  timestamp: string;
}

export interface ReadinessResponse {
  status: "ready" | "degraded";
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  dependencies: Record<string, DependencyStatus>;
}

export type BackendConnectionState = "checking" | "connected" | "degraded" | "unreachable";

export interface PlannedModule {
  readonly key: string;
  readonly name: string;
  readonly stage: string;
  readonly apiBoundary: string;
  readonly summary: string;
}
