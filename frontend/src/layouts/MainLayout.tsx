import type { ReactNode } from "react";
import { StatusBadge, type StatusTone } from "../components/StatusBadge/StatusBadge";
import { env } from "../config/env";
import type { BackendConnectionState } from "../types/health";
import styles from "./MainLayout.module.css";

export type PlatformSection = "overview" | "data-management";

export interface MainLayoutProps {
  readonly connectionState: BackendConnectionState;
  readonly activeSection?: PlatformSection;
  readonly onNavigateSection?: (section: PlatformSection) => void;
  readonly children: ReactNode;
}

function mapConnectionToHeaderBadge(state: BackendConnectionState): {
  tone: StatusTone;
  label: string;
} {
  switch (state) {
    case "connected":
      return { tone: "connected", label: "API Connected" };
    case "degraded":
      return { tone: "degraded", label: "API Degraded" };
    case "unreachable":
      return { tone: "unreachable", label: "API Offline" };
    default:
      return { tone: "checking", label: "Checking API" };
  }
}

export function MainLayout({
  connectionState,
  activeSection = "overview",
  onNavigateSection,
  children,
}: MainLayoutProps) {
  const badge = mapConnectionToHeaderBadge(connectionState);

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.brand}>
            <svg className={styles.logoMark} viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <rect width="32" height="32" rx="6" fill="#0F172A" />
              <path d="M8 10h16v3H8zM8 15h11v3H8zM8 20h16v3H8z" fill="#F8FAFC" />
              <circle cx="23" cy="16.5" r="2.2" fill="#2563EB" />
            </svg>
            <div className={styles.brandText}>
              <span className={styles.brandTitle}>{env.appName}</span>
              <span className={styles.brandSub}>Modular Enterprise Intelligence</span>
            </div>
          </div>

          {onNavigateSection ? (
            <nav className={styles.navTabs} aria-label="Primary sections">
              <button
                type="button"
                className={`${styles.navTab} ${activeSection === "overview" ? styles.navTabActive : ""}`}
                aria-current={activeSection === "overview" ? "page" : undefined}
                onClick={() => onNavigateSection("overview")}
              >
                Platform Overview
              </button>
              <button
                type="button"
                className={`${styles.navTab} ${activeSection === "data-management" ? styles.navTabActive : ""}`}
                aria-current={activeSection === "data-management" ? "page" : undefined}
                onClick={() => onNavigateSection("data-management")}
              >
                Data Management
              </button>
            </nav>
          ) : null}

          <div className={styles.headerControls}>
            <span className={styles.stageTag}>Stage 2 · v0.2.0</span>
            <StatusBadge tone={badge.tone} label={badge.label} />
            <a
              className={styles.docsLink}
              href={`${env.apiBaseUrl}/docs`}
              target="_blank"
              rel="noreferrer"
            >
              OpenAPI Docs
            </a>
          </div>
        </div>
      </header>

      <main className={styles.main}>{children}</main>

      <footer className={styles.footer}>
        <div className={styles.footerInner}>
          <span>{env.appName} — Enterprise Data &amp; Architecture Shell</span>
          <span>Modular Monolith · Stage 2 Data Integration Active</span>
        </div>
      </footer>
    </div>
  );
}
