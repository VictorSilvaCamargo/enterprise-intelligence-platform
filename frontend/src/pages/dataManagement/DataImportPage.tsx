import { useRef, useState, type ChangeEvent } from "react";
import { importDataSourceFile, previewDataSourceFile } from "../../services/dataManagementService";
import type { FilePreviewResponse, ImportExecutionResponse } from "../../types/dataManagement";
import styles from "./DataManagement.module.css";
import {
  formatBytes,
  formatCellValue,
  getQualityScorePillClass,
  getStatusPillClass,
} from "./formatters";

export interface DataImportPageProps {
  readonly onImportCompleted: (dataSourceId: string) => void;
}

function defaultSourceNameFromFile(filename: string): string {
  const withoutExt = filename.replace(/\.[^.]+$/, "");
  return withoutExt.replace(/[_-]+/g, " ").trim();
}

export function DataImportPage({ onImportCompleted }: DataImportPageProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [sourceName, setSourceName] = useState("");
  const [selectedSheet, setSelectedSheet] = useState<string>("");
  const [skipDuplicates, setSkipDuplicates] = useState(false);

  const [preview, setPreview] = useState<FilePreviewResponse | null>(null);
  const [importResult, setImportResult] = useState<ImportExecutionResponse | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setSelectedFile(file);
    setPreview(null);
    setImportResult(null);
    setError(null);
    setSelectedSheet("");
    if (file) {
      setSourceName(defaultSourceNameFromFile(file.name));
    } else {
      setSourceName("");
    }
  };

  const runPreview = async (file: File, sheet?: string) => {
    setIsPreviewing(true);
    setError(null);
    setImportResult(null);
    try {
      const response = await previewDataSourceFile(file, sheet);
      setPreview(response);
      setSelectedSheet(response.selected_sheet ?? "");
    } catch (err) {
      setPreview(null);
      setError(err instanceof Error ? err.message : "Failed to preview uploaded file.");
    } finally {
      setIsPreviewing(false);
    }
  };

  const handlePreviewClick = async () => {
    if (!selectedFile) {
      setError("Select a CSV, XLSX, or JSON file before running preview.");
      return;
    }
    await runPreview(selectedFile, selectedSheet || undefined);
  };

  const handleSheetChange = async (event: ChangeEvent<HTMLSelectElement>) => {
    const nextSheet = event.target.value;
    setSelectedSheet(nextSheet);
    if (selectedFile) {
      await runPreview(selectedFile, nextSheet);
    }
  };

  const handleConfirmImport = async () => {
    if (!selectedFile || !preview) {
      return;
    }
    setIsImporting(true);
    setError(null);
    try {
      const result = await importDataSourceFile({
        file: selectedFile,
        name: sourceName.trim() || undefined,
        sheetName: preview.selected_sheet ?? undefined,
        skipDuplicates,
      });
      setImportResult(result);
      setPreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to execute import.");
    } finally {
      setIsImporting(false);
    }
  };

  const handleCancelPreview = () => {
    setPreview(null);
    setSelectedFile(null);
    setSourceName("");
    setSelectedSheet("");
    setSkipDuplicates(false);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  return (
    <div className={styles.container}>
      <section className={styles.card} aria-labelledby="import-upload-heading">
        <div className={styles.cardHeader}>
          <div>
            <h2 id="import-upload-heading" className={styles.cardTitle}>
              Upload &amp; Validate File
            </h2>
            <p className={styles.cardSubtitle}>
              Supported formats: CSV, XLSX (multi-sheet), and JSON arrays. Preview validation before
              persisting into PostgreSQL.
            </p>
          </div>
        </div>

        <div className={styles.dropzone}>
          <label htmlFor="dataset-file-input" className={styles.fieldLabel}>
            Select Dataset File (.csv, .xlsx, .json)
          </label>
          <input
            ref={fileInputRef}
            id="dataset-file-input"
            type="file"
            accept=".csv,.xlsx,.json"
            onChange={handleFileChange}
          />
          {selectedFile ? (
            <span className={styles.fileMeta}>
              Selected: {selectedFile.name} ({formatBytes(selectedFile.size)})
            </span>
          ) : (
            <span className={styles.cardSubtitle}>
              Maximum upload size enforced by backend configuration (default 10 MB).
            </span>
          )}
        </div>

        <div className={styles.formGrid}>
          <div className={styles.fieldGroup}>
            <label htmlFor="source-name-input" className={styles.fieldLabel}>
              Data Source Name
            </label>
            <input
              id="source-name-input"
              type="text"
              className={styles.input}
              placeholder="e.g., Enterprise Sales Q2"
              value={sourceName}
              onChange={(e) => setSourceName(e.target.value)}
            />
          </div>

          {preview && preview.available_sheets.length > 1 ? (
            <div className={styles.fieldGroup}>
              <label htmlFor="sheet-select" className={styles.fieldLabel}>
                Excel Worksheet
              </label>
              <select
                id="sheet-select"
                className={styles.select}
                value={selectedSheet}
                onChange={handleSheetChange}
                disabled={isPreviewing}
              >
                {preview.available_sheets.map((sheet) => (
                  <option key={sheet} value={sheet}>
                    {sheet}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
        </div>

        <div className={styles.buttonRow}>
          <button
            type="button"
            className={styles.primaryButton}
            onClick={handlePreviewClick}
            disabled={!selectedFile || isPreviewing || isImporting}
          >
            {isPreviewing ? "Analyzing File..." : "Preview & Validate"}
          </button>
          {preview ? (
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={handleCancelPreview}
              disabled={isImporting}
            >
              Cancel Import
            </button>
          ) : null}
        </div>

        {error ? (
          <div className={`${styles.alert} ${styles.alertError}`} role="alert">
            {error}
          </div>
        ) : null}

        {importResult ? (
          <div className={`${styles.alert} ${styles.alertSuccess}`} role="status">
            <strong>Import Completed:</strong> Source &ldquo;{importResult.data_source.name}&rdquo;
            created with <strong>{importResult.data_source.record_count}</strong> persisted
            record(s) (Job status:{" "}
            <span className={getStatusPillClass(importResult.import_job.status)}>
              {importResult.import_job.status}
            </span>
            , Quality score:{" "}
            <strong>{importResult.quality_report.overall_score.toFixed(1)}%</strong>
            ).{" "}
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => onImportCompleted(importResult.data_source.id)}
            >
              Explore Imported Records
            </button>
          </div>
        ) : null}
      </section>

      {preview ? (
        <>
          <section className={styles.card} aria-labelledby="validation-report-heading">
            <div className={styles.cardHeader}>
              <div>
                <h2 id="validation-report-heading" className={styles.cardTitle}>
                  ETL Validation &amp; Quality Report
                </h2>
                <p className={styles.cardSubtitle}>{preview.quality_report.methodology}</p>
              </div>
              <span className={getQualityScorePillClass(preview.quality_report.overall_score)}>
                Quality Score: {preview.quality_report.overall_score.toFixed(1)}%
              </span>
            </div>

            <div className={styles.kpiGrid}>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>Records Received</span>
                <span className={styles.kpiValue}>{preview.records_received}</span>
                <span className={styles.kpiMeta}>Format: {preview.file_type.toUpperCase()}</span>
              </div>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>Valid / Rejected</span>
                <span className={styles.kpiValue}>
                  {preview.records_valid} / {preview.records_rejected}
                </span>
                <span className={styles.kpiMeta}>
                  Validity: {preview.quality_report.validity_rate.toFixed(1)}%
                </span>
              </div>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>Duplicates Found</span>
                <span className={styles.kpiValue}>{preview.duplicates_found}</span>
                <span className={styles.kpiMeta}>
                  Uniqueness: {preview.quality_report.uniqueness_rate.toFixed(1)}%
                </span>
              </div>
              <div className={styles.kpiCard}>
                <span className={styles.kpiLabel}>Missing Values</span>
                <span className={styles.kpiValue}>{preview.missing_values_count}</span>
                <span className={styles.kpiMeta}>
                  Completeness: {preview.quality_report.completeness_rate.toFixed(1)}%
                </span>
              </div>
            </div>

            {preview.formatting_issues.length > 0 ? (
              <div className={`${styles.alert} ${styles.alertWarning}`}>
                <strong>
                  Formatting &amp; Normalization Notes ({preview.formatting_issues.length}):
                </strong>
                <ul className={styles.list}>
                  {preview.formatting_issues.slice(0, 8).map((issue, idx) => (
                    <li key={`${idx}-${issue}`}>{issue}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            <div className={styles.tableWrapper}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Normalized Column</th>
                    <th>Original Header</th>
                    <th>Inferred Type</th>
                    <th>Non-Null</th>
                    <th>Missing</th>
                    <th>Type Errors</th>
                    <th>Distinct</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.quality_report.column_profiles.map((col) => (
                    <tr key={col.column_name}>
                      <td className={styles.mono}>{col.column_name}</td>
                      <td>{col.original_name}</td>
                      <td>
                        <span className={`${styles.pill} ${styles.pillBrand}`}>
                          {col.inferred_type}
                        </span>
                      </td>
                      <td>{col.non_null_count}</td>
                      <td>
                        {col.missing_count} ({col.missing_rate.toFixed(1)}%)
                      </td>
                      <td>{col.type_error_count}</td>
                      <td>{col.distinct_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {preview.rejected_rows.length > 0 ? (
              <div className={`${styles.alert} ${styles.alertError}`}>
                <strong>Rejected Rows ({preview.records_rejected}):</strong>
                <div className={styles.tableWrapper} style={{ marginTop: "0.5rem" }}>
                  <table className={styles.table}>
                    <thead>
                      <tr>
                        <th>Row #</th>
                        <th>Rejection Reasons</th>
                        <th>Raw Content</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rejected_rows.map((rej) => (
                        <tr key={rej.row_number}>
                          <td className={styles.mono}>{rej.row_number}</td>
                          <td>{rej.reasons.join("; ")}</td>
                          <td className={styles.mono}>{JSON.stringify(rej.raw_content)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : null}
          </section>

          <section className={styles.card} aria-labelledby="preview-sample-heading">
            <div className={styles.cardHeader}>
              <div>
                <h2 id="preview-sample-heading" className={styles.cardTitle}>
                  Normalized Data Preview (First {preview.sample_rows.length} Valid Row(s))
                </h2>
                <p className={styles.cardSubtitle}>
                  Review cleaned columns and values before committing to PostgreSQL.
                </p>
              </div>
              <div className={styles.buttonRow}>
                <label className={styles.checkboxLabel}>
                  <input
                    type="checkbox"
                    checked={skipDuplicates}
                    onChange={(e) => setSkipDuplicates(e.target.checked)}
                  />
                  Skip duplicate records on import
                </label>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={handleCancelPreview}
                  disabled={isImporting}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className={styles.primaryButton}
                  onClick={handleConfirmImport}
                  disabled={isImporting || preview.records_valid === 0}
                >
                  {isImporting ? "Persisting Records..." : "Confirm Import"}
                </button>
              </div>
            </div>

            {preview.sample_rows.length === 0 ? (
              <div className={styles.emptyState}>
                No valid rows available to preview. Fix source validation errors before importing.
              </div>
            ) : (
              <div className={styles.tableWrapper}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      {preview.columns.map((col) => (
                        <th key={col}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.sample_rows.map((row, rowIndex) => (
                      <tr key={rowIndex}>
                        {preview.columns.map((col) => (
                          <td key={col}>{formatCellValue(row[col])}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}
