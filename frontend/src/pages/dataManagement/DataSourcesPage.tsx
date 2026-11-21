import { useEffect, useState } from "react";
import {
  getDataSourceDetail,
  getDataSourceQuality,
  listDataSources,
} from "../../services/dataManagementService";
import type {
  DataSourceDetail,
  DataSourceSummary,
  QualityReport,
} from "../../types/dataManagement";
import styles from "./DataManagement.module.css";
import {
  formatDateTime,
  formatNumber,
  getQualityScorePillClass,
  getStatusPillClass,
} from "./formatters";

export interface DataSourcesPageProps {
  readonly initialSelectedSourceId?: string;
  readonly onExploreSource: (sourceId: string) => void;
}

export function DataSourcesPage({
  initialSelectedSourceId,
  onExploreSource,
}: DataSourcesPageProps) {
  const [sources, setSources] = useState<DataSourceSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState("");
  const [fileType, setFileType] = useState("");

  const [selectedId, setSelectedId] = useState<string | null>(initialSelectedSourceId ?? null);
  const [detail, setDetail] = useState<DataSourceDetail | null>(null);
  const [quality, setQuality] = useState<QualityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    void listDataSources(
      {
        page,
        pageSize: 10,
        search: search || undefined,
        fileType: fileType || undefined,
      },
      controller.signal,
    )
      .then((res) => {
        if (active) {
          setSources(res.items);
          setTotal(res.total);
          setTotalPages(res.total_pages);
          setError(null);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active && !controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Failed to load data sources.");
          setLoading(false);
        }
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [page, search, fileType]);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    let active = true;
    const controller = new AbortController();

    void Promise.all([
      getDataSourceDetail(selectedId, controller.signal),
      getDataSourceQuality(selectedId, controller.signal).catch(() => null),
    ])
      .then(([sourceDetail, qualityReport]) => {
        if (active) {
          setDetail(sourceDetail);
          setQuality(qualityReport);
          setDetailLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active && !controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Failed to load source details.");
          setDetailLoading(false);
        }
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [selectedId]);

  return (
    <div className={styles.container}>
      {error ? (
        <div className={`${styles.alert} ${styles.alertError}`} role="alert">
          {error}
        </div>
      ) : null}

      <section className={styles.card} aria-labelledby="sources-list-heading">
        <div className={styles.cardHeader}>
          <div>
            <h2 id="sources-list-heading" className={styles.cardTitle}>
              Registered Data Sources ({formatNumber(total)})
            </h2>
            <p className={styles.cardSubtitle}>
              Inspect ingested schemas, quality metrics, and execution history per source.
            </p>
          </div>
        </div>

        <div className={styles.filterBar}>
          <div className={styles.filterControl}>
            <label htmlFor="sources-search-input" className={styles.fieldLabel}>
              Search Source or Filename
            </label>
            <input
              id="sources-search-input"
              type="text"
              className={styles.input}
              placeholder="Filter by name..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>

          <div className={styles.filterControl}>
            <label htmlFor="sources-format-select" className={styles.fieldLabel}>
              File Format
            </label>
            <select
              id="sources-format-select"
              className={styles.select}
              value={fileType}
              onChange={(e) => {
                setFileType(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All Formats</option>
              <option value="csv">CSV</option>
              <option value="xlsx">XLSX</option>
              <option value="json">JSON</option>
            </select>
          </div>
        </div>

        {loading && sources.length === 0 ? (
          <div className={styles.emptyState}>Loading data sources...</div>
        ) : sources.length === 0 ? (
          <div className={styles.emptyState}>No matching data sources found.</div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Format</th>
                  <th>Original File</th>
                  <th>Records</th>
                  <th>Quality</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sources.map((src) => (
                  <tr
                    key={src.id}
                    className={src.id === selectedId ? styles.rowSelected : undefined}
                  >
                    <td>
                      <strong>{src.name}</strong>
                      {src.sheet_name ? (
                        <div className={styles.mono}>Sheet: {src.sheet_name}</div>
                      ) : null}
                    </td>
                    <td>
                      <span className={`${styles.pill} ${styles.pillBrand}`}>
                        {src.file_type.toUpperCase()}
                      </span>
                    </td>
                    <td className={styles.mono}>{src.original_filename}</td>
                    <td>{formatNumber(src.record_count)}</td>
                    <td>
                      <span className={getQualityScorePillClass(src.latest_quality_score)}>
                        {src.latest_quality_score !== null
                          ? `${src.latest_quality_score.toFixed(1)}%`
                          : "—"}
                      </span>
                    </td>
                    <td>
                      <span className={getStatusPillClass(src.status)}>{src.status}</span>
                    </td>
                    <td>{formatDateTime(src.created_at)}</td>
                    <td>
                      <div className={styles.buttonRow}>
                        <button
                          type="button"
                          className={styles.secondaryButton}
                          onClick={() => {
                            setDetailLoading(true);
                            setSelectedId(src.id);
                          }}
                        >
                          Inspect
                        </button>
                        <button
                          type="button"
                          className={styles.primaryButton}
                          onClick={() => onExploreSource(src.id)}
                        >
                          Explore
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className={styles.paginationRow}>
          <span>
            Page {page} of {totalPages} ({formatNumber(total)} total)
          </span>
          <div className={styles.buttonRow}>
            <button
              type="button"
              className={styles.secondaryButton}
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </button>
            <button
              type="button"
              className={styles.secondaryButton}
              disabled={page >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Next
            </button>
          </div>
        </div>
      </section>

      {selectedId ? (
        <section className={styles.card} aria-labelledby="source-detail-heading">
          {detailLoading || !detail ? (
            <div className={styles.emptyState}>Loading data source details...</div>
          ) : (
            <>
              <div className={styles.cardHeader}>
                <div>
                  <h3 id="source-detail-heading" className={styles.cardTitle}>
                    Source Detail: {detail.name}
                  </h3>
                  <p className={styles.cardSubtitle}>
                    File: {detail.original_filename} · Distinct records:{" "}
                    {formatNumber(detail.stats.distinct_records)} · Flagged duplicates:{" "}
                    {formatNumber(detail.stats.duplicate_records)}
                  </p>
                </div>
                <button
                  type="button"
                  className={styles.primaryButton}
                  onClick={() => onExploreSource(detail.id)}
                >
                  Open in Data Explorer
                </button>
              </div>

              {quality ? (
                <div className={styles.meterList}>
                  <div className={styles.meterItem}>
                    <div className={styles.meterHeader}>
                      <span>Completeness</span>
                      <strong>{quality.completeness_rate.toFixed(1)}%</strong>
                    </div>
                    <div className={styles.meterTrack}>
                      <div
                        className={styles.meterFill}
                        style={{ width: `${quality.completeness_rate}%` }}
                      />
                    </div>
                  </div>
                  <div className={styles.meterItem}>
                    <div className={styles.meterHeader}>
                      <span>Validity</span>
                      <strong>{quality.validity_rate.toFixed(1)}%</strong>
                    </div>
                    <div className={styles.meterTrack}>
                      <div
                        className={styles.meterFill}
                        style={{ width: `${quality.validity_rate}%` }}
                      />
                    </div>
                  </div>
                  <div className={styles.meterItem}>
                    <div className={styles.meterHeader}>
                      <span>Uniqueness</span>
                      <strong>{quality.uniqueness_rate.toFixed(1)}%</strong>
                    </div>
                    <div className={styles.meterTrack}>
                      <div
                        className={styles.meterFill}
                        style={{ width: `${quality.uniqueness_rate}%` }}
                      />
                    </div>
                  </div>
                  <div className={styles.meterItem}>
                    <div className={styles.meterHeader}>
                      <span>Type Consistency</span>
                      <strong>{quality.type_consistency_rate.toFixed(1)}%</strong>
                    </div>
                    <div className={styles.meterTrack}>
                      <div
                        className={styles.meterFill}
                        style={{ width: `${quality.type_consistency_rate}%` }}
                      />
                    </div>
                  </div>
                </div>
              ) : null}

              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Job ID</th>
                      <th>Status</th>
                      <th>Received</th>
                      <th>Valid</th>
                      <th>Rejected</th>
                      <th>Duplicates</th>
                      <th>Started At</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.recent_jobs.map((job) => (
                      <tr key={job.id}>
                        <td className={styles.mono}>{job.id.slice(0, 8)}...</td>
                        <td>
                          <span className={getStatusPillClass(job.status)}>{job.status}</span>
                        </td>
                        <td>{job.records_received}</td>
                        <td>{job.records_valid}</td>
                        <td>{job.records_rejected}</td>
                        <td>{job.duplicates_found}</td>
                        <td>{formatDateTime(job.started_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      ) : null}
    </div>
  );
}
