import type { CanonicalStatus } from "@/lib/types/analytics";

/**
 * Paleta canónica del Manifiesto JPDS (Documento 03.1 Ritmo Operativo).
 * Espejo de backend/src/forge/services/canonical_status.py — única fuente de verdad
 * de colores por estado canónico. CAPA DE DISPLAY (no de atribución de tiempo).
 */
export const CANONICAL_ORDER: CanonicalStatus[] = [
  "Backlog",
  "Ready",
  "In Progress",
  "In Review",
  "In QA",
  "Waiting",
  "Blocked",
  "Done",
  "Cancelled",
];

export const CANONICAL_COLORS: Record<CanonicalStatus, string> = {
  Backlog: "#60A5FA",
  Ready: "#CBD5E1",
  "In Progress": "#FDE68A",
  "In Review": "#DDD6FE",
  "In QA": "#99F6E4",
  Waiting: "#C7D2FE",
  Blocked: "#FCA5A5",
  Done: "#4ADE80",
  Cancelled: "#94A3B8",
};

/**
 * Estados canónicos que SÍ se miden en tiempo (buckets WP-07h). Backlog/Ready/
 * Done/Cancelled son pre-inicio o terminales → no tienen horas medidas.
 */
export const MEASURED_CANONICAL: CanonicalStatus[] = [
  "In Progress",
  "In Review",
  "In QA",
  "Waiting",
  "Blocked",
];

export function canonicalColor(status: string): string {
  return CANONICAL_COLORS[status as CanonicalStatus] ?? "#E5E7EB";
}
