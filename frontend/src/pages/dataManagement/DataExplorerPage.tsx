import { useEffect, useState } from "react";
import {
  getRecordDetail,
  listDataSourceRecords,
  listDataSources,
} from "../../services/dataManagementService";
import type {
  DataSourceSummary,
  ImportedRecordDetail,
  ImportedRecordSummary,
} from "../../types/dataManagement";
import styles from "./DataManagement.module.css";
import { formatCellValue, formatDateTime, formatNumber } from "./formatters";

export interface DataExplorerPageProps {
  readonly initialSourceId?: string;
}

export function DataExplorerPage({ initialSourceId }: DataExplorerPageProps) {
  const [sources, setSources] = useState<DataSourceSummary[]>([]);
  const [selectedSourceId, setSelectedSourceId] = useState<string>(initialSourceId ?? "");

  const [records, setRecords] = useState<ImportedRecordSummary[]>([]);
  const [columns, setColumns] = useState<string[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const [search, setSearch] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [fieldName, setFieldName] = useState("");
  const [fieldValue, setFieldValue] = useState("");
  const [includeDuplicates, setIncludeDuplicates] = useState(true);

  const [selectedRecord, setSelectedRecord] = useState<ImportedRecordDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const loadSources = async () => {
      try {
        const res = await listDataSources({ page: 1, pageSize: 100 }, controller.signal);
        setSources(res.items);
        if (res.items.length > 0) {
          setSelectedSourceId((current) => current || res.items[0].id);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Failed to load data sources.");
        }
      }
    };
    void loadSources();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!selectedSourceId) {
      return;
    }
    let active = true;
    const controller = new AbortController();

    void listDataSourceRecords(
      selectedSourceId,
      {
        page,
        pageSize: 15,
        search: search || undefined,
        dateFrom: dateFrom || undefined,
        dateTo: dateTo || undefined,
        fieldName: fieldName || undefined,
        fieldValue: fieldValue || undefined,
        includeDuplicates,
      },
      controller.signal,
    )
      .then((res) => {
        if (active) {
          setRecords(res.items);
          setColumns(res.columns);
          setTotal(res.total);
          setTotalPages(res.total_pages);
          setError(null);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (active && !controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Failed to query imported records.");
          setLoading(false);
        }
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [selectedSourceId, page, search, dateFrom, dateTo, fieldName, fieldValue, includeDuplicates]);

  const handleInspectRecord = async (recordId: string) => {
    if (!selectedSourceId) {
      return;
    }
    try {
      const detail = await getRecordDetail(selectedSourceId, recordId);
      setSelectedRecord(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load record details.");
    }
  };

  const handleClearFilters = () => {
    setSearch("");
    setDateFrom("");
    setDateTo("");
    setFieldName("");
    setFieldValue("");
    setIncludeDuplicates(true);
    setPage(1);
  };

  return (
    <div className={styles.container}>
      {error ? (
        <div className={`${styles.alert} ${styles.alertError}`} role="alert">
          {error}
        </div>
      ) : null}

      <section className={styles.card} aria-labelledby="explorer-heading">
        <div className={styles.cardHeader}>
          <div>
            <h2 id="explorer-heading" className={styles.cardTitle}>
              Data Explorer ({formatNumber(total)} matching record(s))
            </h2>
            <p className={styles.cardSubtitle}>
              Search, filter by period or field values, paginate, and inspect raw traceability.
            </p>
          </div>
          <button type="button" className={styles.secondaryButton} onClick={handleClearFilters}>
            Clear Filters
          </button>
        </div>

        <div className={styles.filterBar}>
          <div className={styles.filterControl}>
            <label htmlFor="explorer-source-select" className={styles.fieldLabel}>
              Data Source
            </label>
            <select
              id="explorer-source-select"
              className={styles.select}
              value={selectedSourceId}
              onChange={(e) => {
                setSelectedSourceId(e.target.value);
                setFieldName("");
                setFieldValue("");
                setPage(1);
              }}
            >
              {sources.length === 0 ? <option value="">No data sources available</option> : null}
              {sources.map((src) => (
                <option key={src.id} value={src.id}>
                  {src.name} ({src.file_type.toUpperCase()})
                </option>
              ))}
            </select>
          </div>

          <div className={styles.filterControl}>
            <label htmlFor="explorer-search-input" className={styles.fieldLabel}>
              Full-Text Search
            </label>
            <input
              id="explorer-search-input"
              type="text"
              className={styles.input}
              placeholder="Search any field..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>

          <div className={styles.filterControl}>
            <label htmlFor="explorer-date-from" className={styles.fieldLabel}>
              Imported From
            </label>
            <input
              id="explorer-date-from"
              type="date"
              className={styles.input}
              value={dateFrom}
              onChange={(e) => {
                setDateFrom(e.target.value);
                setPage(1);
              }}
            />
          </div>

          <div className={styles.filterControl}>
            <label htmlFor="explorer-date-to" className={styles.fieldLabel}>
              Imported To
            </label>
            <input
              id="explorer-date-to"
              type="date"
              className={styles.input}
              value={dateTo}
              onChange={(e) => {
                setDateTo(e.target.value);
                setPage(1);
              }}
            />
          </div>
        </div>

        <div className={styles.filterBar}>
          <div className={styles.filterControl}>
            <label htmlFor="explorer-field-name" className={styles.fieldLabel}>
              Field Filter
            </label>
            <select
              id="explorer-field-name"
              className={styles.select}
              value={fieldName}
              onChange={(e) => {
                setFieldName(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Any Field</option>
              {columns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
          </div>

          <div className={styles.filterControl}>
            <label htmlFor="explorer-field-value" className={styles.fieldLabel}>
              Field Value Contains
            </label>
            <input
              id="explorer-field-value"
              type="text"
              className={styles.input}
              placeholder="Enter field value..."
              value={fieldValue}
              disabled={!fieldName}
              onChange={(e) => {
                setFieldValue(e.target.value);
                setPage(1);
              }}
            />
          </div>

          <label className={styles.checkboxLabel} style={{ paddingBottom: "0.45rem" }}>
            <input
              type="checkbox"
              checked={includeDuplicates}
              onChange={(e) => {
                setIncludeDuplicates(e.target.checked);
                setPage(1);
              }}
            />
            Include flagged duplicates
          </label>
        </div>

        {loading && records.length === 0 ? (
          <div className={styles.emptyState}>Loading imported records...</div>
        ) : records.length === 0 ? (
          <div className={styles.emptyState}>
            No records match the current selection or filter criteria.
          </div>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>Row #</th>
                  {columns.map((col) => (
                    <th key={col}>{col}</th>
                  ))}
                  <th>Flags</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {records.map((rec) => (
                  <tr key={rec.id}>
                    <td className={styles.mono}>{rec.row_number}</td>
                    {columns.map((col) => (
                      <td key={col}>{formatCellValue(rec.content[col])}</td>
                    ))}
                    <td>
                      {rec.is_duplicate ? (
                        <span className={`${styles.pill} ${styles.pillWarning}`}>Duplicate</span>
                      ) : (
                        <span className={`${styles.pill} ${styles.pillSuccess}`}>Unique</span>
                      )}
                    </td>
                    <td>
                      <button
                        type="button"
                        className={styles.secondaryButton}
                        onClick={() => handleInspectRecord(rec.id)}
                      >
                        Details
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className={styles.paginationRow}>
          <span>
            Page {page} of {totalPages} ({formatNumber(total)} total records)
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

      {selectedRecord ? (
        <div className={styles.modalBackdrop} role="dialog" aria-modal="true" aria-labelledby="record-modal-title">
          <div className={styles.modalPanel}>
            <div className={styles.cardHeader}>
              <div>
                <h3 id="record-modal-title" className={styles.cardTitle}>
                  Record Detail — Row #{selectedRecord.row_number}
                </h3>
                <p className={styles.cardSubtitle}>
                  Imported at {formatDateTime(selectedRecord.imported_at)} · ID:{" "}
                  <span className={styles.mono}>{selectedRecord.id}</span>
                </p>
              </div>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => setSelectedRecord(null)}
              >
                Close
              </button>
            </div>

            {selectedRecord.validation_warnings.length > 0 ? (
              <div className={`${styles.alert} ${styles.alertWarning}`}>
                <strong>Validation Notes:</strong>
                <ul className={styles.list}>
                  {selectedRecord.validation_warnings.map((warn, idx) => (
                    <li key={`${idx}-${warn}`}>{warn}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className={styles.fieldGroup}>
              <span className={styles.fieldLabel}>Normalized Content (JSONB)</span>
              <pre className={styles.jsonBlock}>
                {JSON.stringify(selectedRecord.content, null, 2)}
              </pre>
            </div>

            <div className={styles.fieldGroup}>
              <span className={styles.fieldLabel}>Original Raw Content (Traceability)</span>
              <pre className={styles.jsonBlock}>
                {JSON.stringify(selectedRecord.raw_content, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
