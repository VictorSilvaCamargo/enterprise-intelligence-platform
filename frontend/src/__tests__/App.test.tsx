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
  version: "0.1.0",
  environment: "development",
  timestamp: "2026-11-19T12:00:00Z",
};

const READINESS_OK = {
  status: "ready",
  service: "Enterprise Intelligence Platform",
  version: "0.1.0",
  environment: "development",
  timestamp: "2026-11-19T12:00:00Z",
  dependencies: {
    postgresql: { status: "up", latency_ms: 2.1, detail: "Connected" },
    redis: { status: "up", latency_ms: 0.9, detail: "Connected" },
  },
};

describe("App overview & connectivity status", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("displays connected status and all five planned architectural modules", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/health/ready")) {
        return jsonResponse(READINESS_OK);
      }
      return jsonResponse(HEALTH_OK);
    });

    render(<App />);

    expect(
      screen.getByRole("heading", { level: 1, name: "Enterprise Intelligence Platform" }),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("API Connected")).toBeInTheDocument();
    });

    expect(screen.getAllByText("Connected").length).toBeGreaterThanOrEqual(3);
    expect(screen.getByText("2.10 ms")).toBeInTheDocument();
    expect(screen.getByText("0.90 ms")).toBeInTheDocument();

    for (const moduleName of [
      "Data Integration",
      "AI Knowledge Hub",
      "AI Agents",
      "Business Intelligence",
      "Workflow Automation",
    ]) {
      expect(screen.getByRole("heading", { level: 3, name: moduleName })).toBeInTheDocument();
    }
  });

  it("displays degraded state when a backing dependency is offline", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/health/ready")) {
        return jsonResponse(
          {
            ...READINESS_OK,
            status: "degraded",
            dependencies: {
              postgresql: { status: "up", latency_ms: 1.5, detail: "Connected" },
              redis: { status: "down", latency_ms: 3001.0, detail: "Connection failed" },
            },
          },
          503,
        );
      }
      return jsonResponse(HEALTH_OK);
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Degraded")).toBeInTheDocument();
    });

    expect(screen.getByText("API Degraded")).toBeInTheDocument();
    expect(screen.getByText("Offline")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("displays unreachable state and recovers after manual verification", async () => {
    const user = userEvent.setup();
    let shouldFail = true;

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      if (shouldFail) {
        throw new TypeError("Network error");
      }
      const url = typeof input === "string" ? input : input.toString();
      if (url.endsWith("/health/ready")) {
        return jsonResponse(READINESS_OK);
      }
      return jsonResponse(HEALTH_OK);
    });

    render(<App />);

    await waitFor(() => {
      expect(screen.getByText("Unreachable")).toBeInTheDocument();
    });
    expect(screen.getByText("API Offline")).toBeInTheDocument();

    shouldFail = false;
    await user.click(screen.getByRole("button", { name: "Verify Connection" }));

    await waitFor(() => {
      expect(screen.getByText("API Connected")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Connected").length).toBeGreaterThanOrEqual(3);
  });
});
