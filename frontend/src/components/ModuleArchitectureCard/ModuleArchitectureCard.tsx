import type { PlannedModule } from "../../types/health";
import { StatusBadge } from "../StatusBadge/StatusBadge";
import styles from "./ModuleArchitectureCard.module.css";

export interface ModuleArchitectureCardProps {
  readonly module: PlannedModule;
}

export function ModuleArchitectureCard({ module }: ModuleArchitectureCardProps) {
  return (
    <article className={styles.card}>
      <div className={styles.header}>
        <div className={styles.titleGroup}>
          <span className={styles.stage}>{module.stage}</span>
          <h3 className={styles.title}>{module.name}</h3>
        </div>
        <StatusBadge tone="planned" label="Planned" />
      </div>
      <p className={styles.summary}>{module.summary}</p>
      <div className={styles.boundary}>
        <span>Extension boundary</span>
        <code className={styles.code}>{module.apiBoundary}</code>
      </div>
    </article>
  );
}
