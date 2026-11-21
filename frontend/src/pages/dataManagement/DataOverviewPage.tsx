import { useCallback, useEffect, useState } from "react";
import { fetchDataManagementOverview } from "../../services/dataManagementService";
import type { DataManagementOverview } from "../../types/dataManagement";
import styles from "./DataManagement.module.css";
import {
  formatDateTime,
  formatNumber,
  getQualityScorePillClass,
  getStatusPillClass,
} from "./formatters";

export interface DataOverviewPageProps {
  readonly onOpenImport: () => void;
  readonly onOpenSources: () => void;
  readonly onOpenExplorer: (sourceId?: string) => void;
}

export function DataOverviewPage({
  onOpenImport,
  onOpenSources,
  onOpenExplorer,
}: DataOverviewPageProps) {
  const [overview, setOverview] = useState<DataManagementOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleRefresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchDataManagementOverview();
      setOverview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load Data Management overview.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    void fetchDataManagementOverview(controller.signal)
      .then((data) => {
        if (active) {
          setOverview(data);
          setError(null);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active && !controller.signal.aborted) {
          setError(
            err instanceof Error ? err.message : "Failed to load Data Management overview.",
          );
          setLoading(false);
        }
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, []);

  return (
    <div className={styles.container}>
      {error ? (
        <div className={`${styles.alert} ${styles.alertError}`} role="alert">
          {error}
        </div>
      ) : null}

      <div className={styles.kpiGrid}>
        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Registered Sources</span>
          <span className={styles.kpiValue}>
            {overview ? formatNumber(overview.total_data_sources) : "—"}
          </span>
          <span className={styles.kpiMeta}>CSV, XLSX &amp; JSON sources</span>
        </div>

        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Imported Records</span>
          <span className={styles.kpiValue}>
            {overview ? formatNumber(overview.total_records) : "—"}
          </span>
          <span className={styles.kpiMeta}>Persisted in PostgreSQL JSONB</span>
        </div>

        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Avg Quality Score</span>
          <span className={styles.kpiValue}>
            {overview ? `${overview.average_quality_score.toFixed(1)}%` : "—"}
          </span>
          <span className={styles.kpiMeta}>
            Completeness:{" "}
            {overview ? `${overview.average_completeness_rate.toFixed(1)}%` : "—"}
          </span>
        </div>

        <div className={styles.kpiCard}>
          <span className={styles.kpiLabel}>Import Executions</span>
          <span className={styles.kpiValue}>
            {overview ? formatNumber(overview.total_import_jobs) : "—"}
          </span>
          <span className={styles.kpiMeta}>
            {overview
              ? `${formatNumber(overview.total_duplicates_found)} duplicates · ${formatNumber(overview.total_records_rejected)} rejected`
              : "Loading metrics"}
          </span>
        </div>
      </div>

      <section className={styles.card} aria-labelledby="overview-quality-heading">
        <div className={styles.cardHeader}>
          <div>
            <h2 id="overview-quality-heading" className={styles.cardTitle}>
              General Quality &amp; Quick Actions
            </h2>
            <p className={styles.cardSubtitle}>
              Aggregated health indicators across all executed import pipelines.
            </p>
          </div>
          <div className={styles.buttonRow}>
            <button type="button" className={styles.primaryButton} onClick={onOpenImport}>
              Import New Dataset
            </button>
            <button type="button" className={styles.secondaryButton} onClick={onOpenSources}>
              Browse Sources
            </button>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => void handleRefresh()}
              disabled={loading}
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>

        {overview ? (
          <div className={styles.meterList}>
            <div className={styles.meterItem}>
              <div className={styles.meterHeader}>
                <span>Average Quality Index</span>
                <strong>{overview.average_quality_score.toFixed(2)}%</strong>
              </div>
              <div className={styles.meterTrack}>
                <div
                  className={styles.meterFill}
                  style={{ width: `${Math.min(100, overview.average_quality_score)}%` }}
                />
              </div>
            </div>
            <div className={styles.meterItem}>
              <div className={styles.meterHeader}>
                <span>Average Field Completeness</span>
                <strong>{overview.average_completeness_rate.toFixed(2)}%</strong>
              </div>
              <div className={styles.meterTrack}>
                <div
                  className={styles.meterFill}
                  style={{ width: `${Math.min(100, overview.average_completeness_rate)}%` }}
                />
              </div>
            </div>
          </div>
        ) : null}
      </section>

      <section className={styles.card} aria-labelledby="recent-imports-heading">
        <div className={styles.cardHeader}>
          <div>
            <h2 id="recent-imports-heading" className={styles.cardTitle}>
              Recent Import Jobs
            </h2>
            <p className={styles.cardSubtitle}>Latest ingestion executions and validation counts.</p>
          </div>
        </div>

        {loading && !overview ? (
          <div className={styles.emptyState}>Loading recent import history...</div>
        ) : overview && overview.recent_import_jobs.length === 0 ? (
          <div className={styles.emptyState}>
            No import jobs recorded yet. Click &ldquo;Import New Dataset&rdquo; to begin.
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Data Source</th>
                  <th>File</th>
                  <th>Format</th>
                  <th>Status</th>
                  <th>Received / Valid / Rejected</th>
                  <th>Quality</th>
                  <th>Executed At</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {overview?.recent_import_jobs.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <strong>{job.data_source_name ?? "Unnamed Source"}</strong>
                    </td>
                    <td className={styles.mono}>{job.original_filename}</td>
                    <td>
                      <span className={`${styles.pill} ${styles.pillBrand}`}>
                        {job.file_type.toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span className={getStatusPillClass(job.status)}>{job.status}</span>
                    </td>
                    <td className={styles.mono}>
                      {job.records_received} / {job.records_valid} / {job.records_rejected}
                    </td>
                    <td>
                      <span className={getQualityScorePillClass(job.quality_score)}>
                        {job.quality_score !== null ? `${job.quality_score.toFixed(1)}%` : "—"}
                      </span>
                    </td>
                    <td>{formatDateTime(job.started_at)}</td>
                    <td>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={() => onOpenExplorer(job.data_source_id)}
                      >
                        Explore
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
