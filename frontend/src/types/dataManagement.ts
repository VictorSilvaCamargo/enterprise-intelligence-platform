export interface ColumnProfile {
  column_name: string;
  original_name: string;
  inferred_type: string;
  non_null_count: number;
  missing_count: number;
  missing_rate: number;
  type_error_count: number;
  distinct_count: number;
}

export interface RejectedRow {
  row_number: number;
  reasons: string[];
  raw_content: Record<string, unknown>;
}

export interface QualityReport {
  completeness_rate: number;
  validity_rate: number;
  uniqueness_rate: number;
  type_consistency_rate: number;
  overall_score: number;
  records_received: number;
  records_valid: number;
  records_rejected: number;
  duplicates_found: number;
  missing_values_count: number;
  formatting_issues_count: number;
  methodology: string;
  column_profiles: ColumnProfile[];
}

export interface FilePreviewResponse {
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  available_sheets: string[];
  selected_sheet: string | null;
  columns: string[];
  original_columns: string[];
  column_mapping: Record<string, string>;
  records_received: number;
  records_valid: number;
  records_rejected: number;
  duplicates_found: number;
  missing_values_count: number;
  formatting_issues: string[];
  rejected_rows: RejectedRow[];
  rejected_rows_truncated: boolean;
  sample_rows: Record<string, unknown>[];
  quality_report: QualityReport;
}

export interface DataSourceSummary {
  id: string;
  name: string;
  file_type: string;
  original_filename: string;
  sheet_name: string | null;
  status: string;
  record_count: number;
  created_at: string;
  updated_at: string;
  latest_quality_score: number | null;
}

export interface DataSourceStats {
  total_records: number;
  duplicate_records: number;
  distinct_records: number;
  total_import_jobs: number;
  first_imported_at: string | null;
  last_imported_at: string | null;
}

export interface ImportJobSummary {
  id: string;
  data_source_id: string;
  data_source_name: string | null;
  started_at: string;
  completed_at: string | null;
  status: string;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  sheet_name: string | null;
  records_received: number;
  records_valid: number;
  records_rejected: number;
  duplicates_found: number;
  missing_values_count: number;
  quality_score: number | null;
  error_messages: string[];
}

export interface ImportJobDetail extends ImportJobSummary {
  quality_summary: Record<string, unknown>;
}

export interface DataSourceDetail extends DataSourceSummary {
  schema_metadata: {
    columns?: string[];
    original_columns?: string[];
    column_mapping?: Record<string, string>;
    column_types?: Record<string, string>;
    formatting_issues?: string[];
  };
  stats: DataSourceStats;
  recent_jobs: ImportJobSummary[];
}

export interface PaginatedDataSourcesResponse {
  items: DataSourceSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PaginatedImportJobsResponse {
  items: ImportJobSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ImportExecutionResponse {
  data_source: DataSourceSummary;
  import_job: ImportJobDetail;
  quality_report: QualityReport;
  rejected_rows: RejectedRow[];
}

export interface ImportedRecordSummary {
  id: string;
  data_source_id: string;
  import_job_id: string;
  row_number: number;
  content: Record<string, unknown>;
  is_duplicate: boolean;
  validation_warnings: string[];
  imported_at: string;
}

export interface ImportedRecordDetail extends ImportedRecordSummary {
  raw_content: Record<string, unknown>;
}

export interface PaginatedRecordsResponse {
  items: ImportedRecordSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  columns: string[];
}

export interface DataManagementOverview {
  total_data_sources: number;
  total_records: number;
  total_import_jobs: number;
  average_quality_score: number;
  average_completeness_rate: number;
  total_duplicates_found: number;
  total_records_rejected: number;
  recent_import_jobs: ImportJobSummary[];
}
