import styles from "./DataManagement.module.css";

export function formatNumber(value: number): string {
  return value.toLocaleString("en-US");
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) {
    return "—";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatCellValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export function getStatusPillClass(status: string): string {
  switch (status) {
    case "active":
    case "completed":
      return `${styles.pill} ${styles.pillSuccess}`;
    case "completed_with_warnings":
    case "processing":
    case "pending":
      return `${styles.pill} ${styles.pillWarning}`;
    case "failed":
    case "archived":
      return `${styles.pill} ${styles.pillDanger}`;
    default:
      return styles.pill;
  }
}

export function getQualityScorePillClass(score: number | null | undefined): string {
  if (score === null || score === undefined) {
    return styles.pill;
  }
  if (score >= 90) {
    return `${styles.pill} ${styles.pillSuccess}`;
  }
  if (score >= 70) {
    return `${styles.pill} ${styles.pillWarning}`;
  }
  return `${styles.pill} ${styles.pillDanger}`;
}
