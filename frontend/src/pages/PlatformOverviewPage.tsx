import { ConnectionStatusPanel } from "../components/ConnectionStatusPanel/ConnectionStatusPanel";
import { ModuleArchitectureCard } from "../components/ModuleArchitectureCard/ModuleArchitectureCard";
import { env } from "../config/env";
import type { UseBackendHealthResult } from "../hooks/useBackendHealth";
import type { PlannedModule } from "../types/health";
import styles from "./PlatformOverviewPage.module.css";

const PLANNED_MODULES: readonly PlannedModule[] = [
  {
    key: "data_integration",
    name: "Data Integration",
    stage: "Stage 2",
    apiBoundary: "/api/v1/data-integration",
    summary:
      "Connectors, ingestion pipelines, schema validation contracts, and relational storage.",
  },
  {
    key: "ai_knowledge_hub",
    name: "AI Knowledge Hub",
    stage: "Stage 4",
    apiBoundary: "/api/v1/knowledge-hub",
    summary:
      "Enterprise document ingestion, chunking, embeddings, and retrieval-augmented generation.",
  },
  {
    key: "ai_agents",
    name: "AI Agents",
    stage: "Stage 5",
    apiBoundary: "/api/v1/agents",
    summary: "Multi-agent task orchestration, specialized tool registries, and execution runtime.",
  },
  {
    key: "business_intelligence",
    name: "Business Intelligence",
    stage: "Stage 6",
    apiBoundary: "/api/v1/intelligence",
    summary: "Analytical KPI queries, executive metrics, and machine learning forecasting models.",
  },
  {
    key: "workflow_automation",
    name: "Workflow Automation",
    stage: "Stage 7",
    apiBoundary: "/api/v1/workflows",
    summary:
      "Event-driven process orchestration, Redis-backed job queues, and scheduled automations.",
  },
];

const FOUNDATION_STACK = [
  "Python 3.12 · FastAPI",
  "SQLAlchemy Async · PostgreSQL",
  "Redis Cache & Queue Base",
  "React · TypeScript · Vite",
  "Docker Compose",
] as const;

export interface PlatformOverviewPageProps {
  readonly health: UseBackendHealthResult;
}

export function PlatformOverviewPage({ health }: PlatformOverviewPageProps) {
  return (
    <div className={styles.page}>
      <section className={styles.intro} aria-labelledby="platform-title">
        <span className={styles.eyebrow}>Stage 1 · Core Architecture Foundation</span>
        <h1 id="platform-title" className={styles.title}>
          {env.appName}
        </h1>
        <p className={styles.lead}>
          A modular enterprise architecture designed to unify data integration, document
          intelligence, multi-agent reasoning, business intelligence, and process automation under
          clean service boundaries and reproducible infrastructure.
        </p>
        <div className={styles.stackRow} aria-label="Core foundation technologies">
          {FOUNDATION_STACK.map((item) => (
            <span key={item} className={styles.stackChip}>
              {item}
            </span>
          ))}
        </div>
      </section>

      <ConnectionStatusPanel health={health} />

      <section className={styles.section} aria-labelledby="planned-modules-heading">
        <div className={styles.sectionHeader}>
          <h2 id="planned-modules-heading" className={styles.sectionTitle}>
            Modular Extension Architecture
          </h2>
          <p className={styles.sectionDescription}>
            Future capabilities will plug into the versioned backend router and isolated domain
            boundaries without altering the core infrastructure layer.
          </p>
        </div>

        <div className={styles.modulesGrid}>
          {PLANNED_MODULES.map((module) => (
            <ModuleArchitectureCard key={module.key} module={module} />
          ))}
        </div>
      </section>
    </div>
  );
}
