import { env } from "../../config/env";
import type { UseBackendHealthResult } from "../../hooks/useBackendHealth";
import type { DependencyStatus } from "../../types/health";
import { StatusBadge, type StatusTone } from "../StatusBadge/StatusBadge";
import styles from "./ConnectionStatusPanel.module.css";

export interface ConnectionStatusPanelProps {
  readonly health: UseBackendHealthResult;
}

function getBadgeForState(state: UseBackendHealthResult["status"]): {
  tone: StatusTone;
  label: string;
} {
  switch (state) {
    case "connected":
      return { tone: "connected", label: "Connected" };
    case "degraded":
      return { tone: "degraded", label: "Degraded" };
    case "unreachable":
      return { tone: "unreachable", label: "Unreachable" };
    default:
      return { tone: "checking", label: "Checking..." };
  }
}

function DependencyTile({
  name,
  dependency,
}: {
  readonly name: string;
  readonly dependency: DependencyStatus | undefined;
}) {
  const tone: StatusTone = dependency
    ? dependency.status === "up"
      ? "connected"
      : "unreachable"
    : "checking";
  const label = dependency ? (dependency.status === "up" ? "Operational" : "Offline") : "Pending";

  return (
    <div className={styles.dependencyCard}>
      <div className={styles.dependencyHeader}>
        <h3 className={styles.dependencyName}>{name}</h3>
        <StatusBadge tone={tone} label={label} />
      </div>
      <dl className={styles.metaList}>
        <div className={styles.metaRow}>
          <dt className={styles.metaLabel}>Detail</dt>
          <dd className={styles.metaValue}>{dependency?.detail ?? "Awaiting readiness probe"}</dd>
        </div>
        <div className={styles.metaRow}>
          <dt className={styles.metaLabel}>Latency</dt>
          <dd className={styles.metaValue}>
            {dependency ? `${dependency.latency_ms.toFixed(2)} ms` : "—"}
          </dd>
        </div>
      </dl>
    </div>
  );
}

export function ConnectionStatusPanel({ health }: ConnectionStatusPanelProps) {
  const overallBadge = getBadgeForState(health.status);
  const postgres = health.readiness?.dependencies.postgresql;
  const redis = health.readiness?.dependencies.redis;
  const isInitialLoad = health.status === "checking" && !health.liveness && !health.errorMessage;

  return (
    <section className={styles.panel} aria-labelledby="connectivity-heading">
      <div className={styles.topBar}>
        <div className={styles.headingGroup}>
          <div className={styles.headingRow}>
            <h2 id="connectivity-heading" className={styles.title}>
              Platform Connectivity Status
            </h2>
            <StatusBadge tone={overallBadge.tone} label={overallBadge.label} />
          </div>
          <p className={styles.subtitle}>
            Live healthcheck verification against FastAPI liveness and infrastructure readiness
            probes.
          </p>
        </div>

        <div className={styles.actions}>
          <button
            type="button"
            className={styles.refreshButton}
            onClick={health.refresh}
            disabled={health.isRefreshing}
          >
            {health.isRefreshing ? "Verifying..." : "Verify Connection"}
          </button>
        </div>
      </div>

      {health.errorMessage && (
        <div
          role="alert"
          className={`${styles.alert} ${health.status === "degraded" ? styles.alertWarning : ""}`}
        >
          {health.errorMessage}
        </div>
      )}

      {isInitialLoad ? (
        <div className={styles.grid} aria-busy="true" aria-label="Checking backend connectivity">
          <div className={styles.skeleton} />
          <div className={styles.skeleton} />
          <div className={styles.skeleton} />
        </div>
      ) : (
        <div className={styles.grid}>
          <div className={styles.dependencyCard}>
            <div className={styles.dependencyHeader}>
              <h3 className={styles.dependencyName}>Backend API</h3>
              <StatusBadge
                tone={health.liveness ? "connected" : "unreachable"}
                label={health.liveness ? "Operational" : "Offline"}
              />
            </div>
            <dl className={styles.metaList}>
              <div className={styles.metaRow}>
                <dt className={styles.metaLabel}>Endpoint</dt>
                <dd className={styles.metaValue}>{env.apiBaseUrl}</dd>
              </div>
              <div className={styles.metaRow}>
                <dt className={styles.metaLabel}>Version / Env</dt>
                <dd className={styles.metaValue}>
                  {health.liveness
                    ? `v${health.liveness.version} (${health.liveness.environment})`
                    : "Unavailable"}
                </dd>
              </div>
            </dl>
          </div>

          <DependencyTile name="PostgreSQL" dependency={postgres} />
          <DependencyTile name="Redis" dependency={redis} />
        </div>
      )}

      <div className={styles.footerNote}>
        <span>
          Endpoints: <code>/health</code> and <code>/health/ready</code>
        </span>
        <span>
          Last verified:{" "}
          {health.lastCheckedAt ? new Date(health.lastCheckedAt).toLocaleTimeString() : "Pending"}
        </span>
      </div>
    </section>
  );
}
