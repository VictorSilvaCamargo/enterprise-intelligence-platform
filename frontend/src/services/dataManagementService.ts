import { buildQueryString, requestJson, requestPostFormData } from "./httpClient";
import type {
  DataManagementOverview,
  DataSourceDetail,
  FilePreviewResponse,
  ImportedRecordDetail,
  ImportExecutionResponse,
  ImportJobDetail,
  PaginatedDataSourcesResponse,
  PaginatedImportJobsResponse,
  PaginatedRecordsResponse,
  QualityReport,
} from "../types/dataManagement";

const API_V1 = "/api/v1";

export async function fetchDataManagementOverview(
  signal?: AbortSignal,
): Promise<DataManagementOverview> {
  const res = await requestJson<DataManagementOverview>(`${API_V1}/data-management/overview`, {
    signal,
  });
  return res.data;
}

export async function previewDataSourceFile(
  file: File,
  sheetName?: string,
  signal?: AbortSignal,
): Promise<FilePreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);
  if (sheetName && sheetName.trim()) {
    formData.append("sheet_name", sheetName.trim());
  }
  const res = await requestPostFormData<FilePreviewResponse>(
    `${API_V1}/data-sources/preview`,
    formData,
    { signal },
  );
  return res.data;
}

export async function importDataSourceFile(
  params: {
    file: File;
    name?: string;
    sheetName?: string;
    skipDuplicates?: boolean;
  },
  signal?: AbortSignal,
): Promise<ImportExecutionResponse> {
  const formData = new FormData();
  formData.append("file", params.file);
  if (params.name && params.name.trim()) {
    formData.append("name", params.name.trim());
  }
  if (params.sheetName && params.sheetName.trim()) {
    formData.append("sheet_name", params.sheetName.trim());
  }
  formData.append("skip_duplicates", String(Boolean(params.skipDuplicates)));

  const res = await requestPostFormData<ImportExecutionResponse>(
    `${API_V1}/data-sources/import`,
    formData,
    { signal },
  );
  return res.data;
}

export async function listDataSources(
  params: {
    page?: number;
    pageSize?: number;
    search?: string;
    fileType?: string;
    status?: string;
  } = {},
  signal?: AbortSignal,
): Promise<PaginatedDataSourcesResponse> {
  const query = buildQueryString({
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
    search: params.search,
    file_type: params.fileType,
    status: params.status,
  });
  const res = await requestJson<PaginatedDataSourcesResponse>(`${API_V1}/data-sources${query}`, {
    signal,
  });
  return res.data;
}

export async function getDataSourceDetail(
  dataSourceId: string,
  signal?: AbortSignal,
): Promise<DataSourceDetail> {
  const res = await requestJson<DataSourceDetail>(`${API_V1}/data-sources/${dataSourceId}`, {
    signal,
  });
  return res.data;
}

export async function getDataSourceQuality(
  dataSourceId: string,
  signal?: AbortSignal,
): Promise<QualityReport> {
  const res = await requestJson<QualityReport>(`${API_V1}/data-sources/${dataSourceId}/quality`, {
    signal,
  });
  return res.data;
}

export async function listDataSourceRecords(
  dataSourceId: string,
  params: {
    page?: number;
    pageSize?: number;
    search?: string;
    dateFrom?: string;
    dateTo?: string;
    fieldName?: string;
    fieldValue?: string;
    includeDuplicates?: boolean;
  } = {},
  signal?: AbortSignal,
): Promise<PaginatedRecordsResponse> {
  const query = buildQueryString({
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
    search: params.search,
    date_from: params.dateFrom,
    date_to: params.dateTo,
    field_name: params.fieldName,
    field_value: params.fieldValue,
    include_duplicates: params.includeDuplicates ?? true,
  });
  const res = await requestJson<PaginatedRecordsResponse>(
    `${API_V1}/data-sources/${dataSourceId}/records${query}`,
    { signal },
  );
  return res.data;
}

export async function getRecordDetail(
  dataSourceId: string,
  recordId: string,
  signal?: AbortSignal,
): Promise<ImportedRecordDetail> {
  const res = await requestJson<ImportedRecordDetail>(
    `${API_V1}/data-sources/${dataSourceId}/records/${recordId}`,
    { signal },
  );
  return res.data;
}

export async function listImportJobs(
  params: {
    page?: number;
    pageSize?: number;
    dataSourceId?: string;
    status?: string;
  } = {},
  signal?: AbortSignal,
): Promise<PaginatedImportJobsResponse> {
  const query = buildQueryString({
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
    data_source_id: params.dataSourceId,
    status: params.status,
  });
  const res = await requestJson<PaginatedImportJobsResponse>(`${API_V1}/import-jobs${query}`, {
    signal,
  });
  return res.data;
}

export async function getImportJobDetail(
  jobId: string,
  signal?: AbortSignal,
): Promise<ImportJobDetail> {
  const res = await requestJson<ImportJobDetail>(`${API_V1}/import-jobs/${jobId}`, { signal });
  return res.data;
}
