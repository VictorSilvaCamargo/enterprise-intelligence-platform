import { useState } from "react";
import { DataExplorerPage } from "./DataExplorerPage";
import { DataImportPage } from "./DataImportPage";
import styles from "./DataManagement.module.css";
import { DataOverviewPage } from "./DataOverviewPage";
import { DataSourcesPage } from "./DataSourcesPage";

export type DataManagementTab = "overview" | "import" | "sources" | "explorer";

const TABS: readonly { key: DataManagementTab; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "import", label: "Import Data" },
  { key: "sources", label: "Data Sources" },
  { key: "explorer", label: "Data Explorer" },
];

export function DataManagementSection() {
  const [activeTab, setActiveTab] = useState<DataManagementTab>("overview");
  const [selectedSourceId, setSelectedSourceId] = useState<string | undefined>(undefined);

  const openExplorer = (sourceId?: string) => {
    if (sourceId) {
      setSelectedSourceId(sourceId);
    }
    setActiveTab("explorer");
  };

  return (
    <div className={styles.container}>
      <section className={styles.sectionHeaderCard} aria-labelledby="dm-title">
        <div className={styles.sectionTopRow}>
          <div>
            <span className={styles.eyebrow}>Stage 2 · Data Integration &amp; Quality</span>
            <h1 id="dm-title" className={styles.pageTitle}>
              Data Management
            </h1>
            <p className={styles.pageLead}>
              Ingest CSV, XLSX, and JSON files, inspect ETL validation reports, monitor data
              quality metrics, and explore persisted enterprise records.
            </p>
          </div>
        </div>

        <div className={styles.subNav} role="tablist" aria-label="Data Management views">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={activeTab === tab.key}
              className={`${styles.subNavButton} ${
                activeTab === tab.key ? styles.subNavButtonActive : ""
              }`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </section>

      {activeTab === "overview" ? (
        <DataOverviewPage
          onOpenImport={() => setActiveTab("import")}
          onOpenSources={() => setActiveTab("sources")}
          onOpenExplorer={openExplorer}
        />
      ) : null}

      {activeTab === "import" ? (
        <DataImportPage onImportCompleted={(sourceId) => openExplorer(sourceId)} />
      ) : null}

      {activeTab === "sources" ? (
        <DataSourcesPage
          initialSelectedSourceId={selectedSourceId}
          onExploreSource={(sourceId) => openExplorer(sourceId)}
        />
      ) : null}

      {activeTab === "explorer" ? <DataExplorerPage initialSourceId={selectedSourceId} /> : null}
    </div>
  );
}
