import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../App";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const HEALTH_OK = {
  status: "ok",
  service: "Enterprise Intelligence Platform",
  version: "0.2.0",
  environment: "test",
  timestamp: "2026-11-21T16:00:00Z",
};

const READINESS_OK = {
  status: "ready",
  service: "Enterprise Intelligence Platform",
  version: "0.2.0",
  environment: "test",
  timestamp: "2026-11-21T16:00:00Z",
  dependencies: {
    postgresql: { status: "up", latency_ms: 1.4, detail: "Connected" },
    redis: { status: "up", latency_ms: 0.6, detail: "Connected" },
  },
};

const OVERVIEW_PAYLOAD = {
  total_data_sources: 2,
  total_records: 100,
  total_import_jobs: 2,
  average_quality_score: 97.5,
  average_completeness_rate: 98.2,
  total_duplicates_found: 2,
  total_records_rejected: 1,
  recent_import_jobs: [
    {
      id: "job-1",
      data_source_id: "src-1",
      data_source_name: "Enterprise Sales CSV",
      started_at: "2026-11-21T15:00:00Z",
      completed_at: "2026-11-21T15:00:02Z",
      status: "completed_with_warnings",
      original_filename: "sales.csv",
      file_type: "csv",
      file_size_bytes: 2048,
      sheet_name: null,
      records_received: 60,
      records_valid: 59,
      records_rejected: 1,
      duplicates_found: 1,
      missing_values_count: 2,
      quality_score: 96.4,
      error_messages: [],
    },
  ],
};

const PREVIEW_PAYLOAD = {
  original_filename: "ops.xlsx",
  file_type: "xlsx",
  file_size_bytes: 4096,
  available_sheets: ["Sales_Orders", "Inventory_Stock"],
  selected_sheet: "Sales_Orders",
  columns: ["order_id", "amount"],
  original_columns: ["Order ID", "Amount"],
  column_mapping: { "Order ID": "order_id", Amount: "amount" },
  records_received: 3,
  records_valid: 2,
  records_rejected: 1,
  duplicates_found: 0,
  missing_values_count: 0,
  formatting_issues: ["Column header 'Order ID' normalized to 'order_id'."],
  rejected_rows: [
    {
      row_number: 3,
      reasons: ["Column 'amount' expected float, got 'BAD'."],
      raw_content: { "Order ID": "ORD-3", Amount: "BAD" },
    },
  ],
  rejected_rows_truncated: false,
  sample_rows: [
    { order_id: "ORD-1", amount: 150.0 },
    { order_id: "ORD-2", amount: 220.5 },
  ],
  quality_report: {
    completeness_rate: 100.0,
    validity_rate: 66.67,
    uniqueness_rate: 100.0,
    type_consistency_rate: 83.33,
    overall_score: 87.5,
    records_received: 3,
    records_valid: 2,
    records_rejected: 1,
    duplicates_found: 0,
    missing_values_count: 0,
    formatting_issues_count: 1,
    methodology: "Weighted quality index (0-100).",
    column_profiles: [
      {
        column_name: "order_id",
        original_name: "Order ID",
        inferred_type: "string",
        non_null_count: 2,
        missing_count: 0,
        missing_rate: 0,
        type_error_count: 0,
        distinct_count: 2,
      },
      {
        column_name: "amount",
        original_name: "Amount",
        inferred_type: "float",
        non_null_count: 2,
        missing_count: 0,
        missing_rate: 0,
        type_error_count: 1,
        distinct_count: 2,
      },
    ],
  },
};

describe("Data Management UI workflows", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("navigates to Data Management Overview, handles Import preview/cancel/confirm, Sources, and Explorer", async () => {
    const user = userEvent.setup();
    let importCalled = false;

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : input.toString();

      if (url.endsWith("/health/ready")) {
        return jsonResponse(READINESS_OK);
      }
      if (url.endsWith("/health")) {
        return jsonResponse(HEALTH_OK);
      }
      if (url.includes("/api/v1/data-management/overview")) {
        return jsonResponse(OVERVIEW_PAYLOAD);
      }
      if (url.includes("/api/v1/data-sources/preview")) {
        const body = init?.body;
        const sheet = body instanceof FormData ? body.get("sheet_name") : null;
        return jsonResponse({
          ...PREVIEW_PAYLOAD,
          selected_sheet: typeof sheet === "string" && sheet ? sheet : "Sales_Orders",
        });
      }
      if (url.includes("/api/v1/data-sources/import")) {
        importCalled = true;
        return jsonResponse(
          {
            data_source: {
              id: "src-new",
              name: "Operations Workbook",
              file_type: "xlsx",
              original_filename: "ops.xlsx",
              sheet_name: "Inventory_Stock",
              status: "active",
              record_count: 2,
              created_at: "2026-11-21T16:10:00Z",
              updated_at: "2026-11-21T16:10:00Z",
              latest_quality_score: 87.5,
            },
            import_job: {
              ...OVERVIEW_PAYLOAD.recent_import_jobs[0],
              id: "job-new",
              data_source_id: "src-new",
              data_source_name: "Operations Workbook",
              status: "completed_with_warnings",
              quality_summary: PREVIEW_PAYLOAD.quality_report,
            },
            quality_report: PREVIEW_PAYLOAD.quality_report,
            rejected_rows: PREVIEW_PAYLOAD.rejected_rows,
          },
          201,
        );
      }
      if (url.includes("/api/v1/data-sources/src-1/records/rec-1")) {
        return jsonResponse({
          id: "rec-1",
          data_source_id: "src-1",
          import_job_id: "job-1",
          row_number: 1,
          content: { order_id: "ORD-1", customer_name: "Acme Corp" },
          raw_content: { "Order ID": "ORD-1", "Customer Name ": "  Acme   Corp " },
          is_duplicate: false,
          validation_warnings: ["Cleaned extraneous whitespace in 1 field(s)."],
          imported_at: "2026-11-21T15:00:02Z",
        });
      }
      if (url.includes("/api/v1/data-sources/src-1/records")) {
        return jsonResponse({
          items: [
            {
              id: "rec-1",
              data_source_id: "src-1",
              import_job_id: "job-1",
              row_number: 1,
              content: { order_id: "ORD-1", customer_name: "Acme Corp" },
              is_duplicate: false,
              validation_warnings: [],
              imported_at: "2026-11-21T15:00:02Z",
            },
          ],
          total: 25,
          page: 1,
          page_size: 15,
          total_pages: 2,
          columns: ["order_id", "customer_name"],
        });
      }
      if (url.includes("/api/v1/data-sources/src-1/quality")) {
        return jsonResponse(PREVIEW_PAYLOAD.quality_report);
      }
      if (url.includes("/api/v1/data-sources/src-1")) {
        return jsonResponse({
          id: "src-1",
          name: "Enterprise Sales CSV",
          file_type: "csv",
          original_filename: "sales.csv",
          sheet_name: null,
          status: "active",
          record_count: 59,
          created_at: "2026-11-21T15:00:00Z",
          updated_at: "2026-11-21T15:00:00Z",
          latest_quality_score: 96.4,
          schema_metadata: { columns: ["order_id", "customer_name"] },
          stats: {
            total_records: 59,
            duplicate_records: 1,
            distinct_records: 58,
            total_import_jobs: 1,
            first_imported_at: "2026-11-21T15:00:02Z",
            last_imported_at: "2026-11-21T15:00:02Z",
          },
          recent_jobs: OVERVIEW_PAYLOAD.recent_import_jobs,
        });
      }
      if (url.includes("/api/v1/data-sources")) {
        return jsonResponse({
          items: [
            {
              id: "src-1",
              name: "Enterprise Sales CSV",
              file_type: "csv",
              original_filename: "sales.csv",
              sheet_name: null,
              status: "active",
              record_count: 59,
              created_at: "2026-11-21T15:00:00Z",
              updated_at: "2026-11-21T15:00:00Z",
              latest_quality_score: 96.4,
            },
          ],
          total: 1,
          page: 1,
          page_size: 10,
          total_pages: 1,
        });
      }

      return jsonResponse({}, 404);
    });

    render(<App />);

    // 1. Switch to Data Management section and verify Overview KPIs
    await user.click(screen.getByRole("button", { name: "Data Management" }));
    expect(screen.getByRole("heading", { level: 1, name: "Data Management" })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("97.5%")).toBeInTheDocument();
    });
    expect(screen.getByText("Enterprise Sales CSV")).toBeInTheDocument();

    // 2. Import Data: preview -> cancel -> preview -> sheet change -> confirm import
    await user.click(screen.getByRole("tab", { name: "Import Data" }));
    const fileInput = screen.getByLabelText("Select Dataset File (.csv, .xlsx, .json)");
    const testFile = new File(["placeholder"], "ops.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });

    await user.upload(fileInput, testFile);
    await user.click(screen.getByRole("button", { name: "Preview & Validate" }));

    await waitFor(() => {
      expect(screen.getByText("Quality Score: 87.5%")).toBeInTheDocument();
    });
    expect(screen.getByText("ORD-1")).toBeInTheDocument();
    expect(screen.getByText("Column 'amount' expected float, got 'BAD'.")).toBeInTheDocument();

    // Cancel without persisting
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(importCalled).toBe(false);
    expect(screen.queryByText("Quality Score: 87.5%")).not.toBeInTheDocument();

    // Upload again, preview, switch Excel sheet, and confirm
    await user.upload(fileInput, testFile);
    await user.click(screen.getByRole("button", { name: "Preview & Validate" }));
    await waitFor(() => {
      expect(screen.getByLabelText("Excel Worksheet")).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText("Excel Worksheet"), "Inventory_Stock");
    await user.click(screen.getByRole("button", { name: "Confirm Import" }));

    await waitFor(() => {
      expect(screen.getByText(/Import Completed:/)).toBeInTheDocument();
    });
    expect(importCalled).toBe(true);

    // 3. Data Sources tab: inspect source details
    await user.click(screen.getByRole("tab", { name: "Data Sources" }));
    await waitFor(() => {
      expect(screen.getByText("Enterprise Sales CSV")).toBeInTheDocument();
    });
    await user.click(screen.getByRole("button", { name: "Inspect" }));
    await waitFor(() => {
      expect(
        screen.getByRole("heading", { level: 3, name: "Source Detail: Enterprise Sales CSV" }),
      ).toBeInTheDocument();
    });

    // 4. Data Explorer tab: list records & inspect raw traceability modal
    await user.click(screen.getByRole("tab", { name: "Data Explorer" }));
    await waitFor(() => {
      expect(screen.getByText("Acme Corp")).toBeInTheDocument();
    });
    expect(screen.getByText("Page 1 of 2 (25 total records)")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Details" }));
    await waitFor(() => {
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });
    expect(screen.getByText("Original Raw Content (Traceability)")).toBeInTheDocument();
    expect(
      screen.getByText(
        (_, node) =>
          node?.tagName === "PRE" && Boolean(node.textContent?.includes("  Acme   Corp ")),
      ),
    ).toBeInTheDocument();
  });
});
