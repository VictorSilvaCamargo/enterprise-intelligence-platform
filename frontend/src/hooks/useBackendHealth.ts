import { useCallback, useEffect, useRef, useState } from "react";
import { env } from "../config/env";
import { fetchLiveness, fetchReadiness } from "../services/healthService";
import type { BackendConnectionState, HealthResponse, ReadinessResponse } from "../types/health";

export interface UseBackendHealthResult {
  readonly status: BackendConnectionState;
  readonly liveness: HealthResponse | null;
  readonly readiness: ReadinessResponse | null;
  readonly lastCheckedAt: string | null;
  readonly errorMessage: string | null;
  readonly isRefreshing: boolean;
  readonly refresh: () => void;
}

interface HealthCheckOutcome {
  readonly status: BackendConnectionState;
  readonly liveness: HealthResponse | null;
  readonly readiness: ReadinessResponse | null;
  readonly errorMessage: string | null;
}

async function probeBackendHealth(signal: AbortSignal): Promise<HealthCheckOutcome> {
  const [livenessResult, readinessResult] = await Promise.allSettled([
    fetchLiveness(signal),
    fetchReadiness(signal),
  ]);

  if (livenessResult.status === "rejected") {
    const reason = livenessResult.reason;
    return {
      status: "unreachable",
      liveness: null,
      readiness: null,
      errorMessage:
        reason instanceof Error ? reason.message : "Backend API service is unreachable.",
    };
  }

  if (readinessResult.status === "rejected") {
    const reason = readinessResult.reason;
    return {
      status: "degraded",
      liveness: livenessResult.value,
      readiness: null,
      errorMessage:
        reason instanceof Error
          ? reason.message
          : "Readiness probe failed to report backing services.",
    };
  }

  const readinessData = readinessResult.value.data;
  const isReady = readinessData.status === "ready";
  return {
    status: isReady ? "connected" : "degraded",
    liveness: livenessResult.value,
    readiness: readinessData,
    errorMessage: isReady
      ? null
      : "Backend API is reachable, but one or more infrastructure dependencies are offline.",
  };
}

export function useBackendHealth(): UseBackendHealthResult {
  const [status, setStatus] = useState<BackendConnectionState>("checking");
  const [liveness, setLiveness] = useState<HealthResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null);
  const [lastCheckedAt, setLastCheckedAt] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const manualAbortRef = useRef<AbortController | null>(null);

  const applyOutcome = useCallback((outcome: HealthCheckOutcome) => {
    setStatus(outcome.status);
    setLiveness(outcome.liveness);
    setReadiness(outcome.readiness);
    setErrorMessage(outcome.errorMessage);
    setLastCheckedAt(new Date().toISOString());
    setIsRefreshing(false);
  }, []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    const poll = () => {
      void probeBackendHealth(controller.signal).then((outcome) => {
        if (active && !controller.signal.aborted) {
          applyOutcome(outcome);
        }
      });
    };

    poll();
    const intervalId = globalThis.setInterval(poll, env.healthPollIntervalMs);

    return () => {
      active = false;
      controller.abort();
      manualAbortRef.current?.abort();
      globalThis.clearInterval(intervalId);
    };
  }, [applyOutcome]);

  const refresh = useCallback(() => {
    manualAbortRef.current?.abort();
    const controller = new AbortController();
    manualAbortRef.current = controller;
    setIsRefreshing(true);

    void probeBackendHealth(controller.signal).then((outcome) => {
      if (!controller.signal.aborted) {
        applyOutcome(outcome);
      }
    });
  }, [applyOutcome]);

  return {
    status,
    liveness,
    readiness,
    lastCheckedAt,
    errorMessage,
    isRefreshing,
    refresh,
  };
}
