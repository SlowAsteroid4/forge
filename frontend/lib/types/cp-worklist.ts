/** Tipos que mapean la respuesta de /api/cp-worklist (WP-24, read-only) */

export interface CpWorklistItem {
  jira_key: string;
  summary: string;
  area: string;
  status: string;
  assignee_player_id: number | null;
  assignee_name: string | null;
  /** Días desde el import a la BD (no es la fecha de creación en Jira). */
  age_days: number;
}

export interface ApartadoGroup {
  apartado: string;
  known: boolean;
  count: number;
  items: CpWorklistItem[];
}

export interface XxlWorklistItem {
  jira_key: string;
  summary: string;
  area: string;
  status: string;
  assignee_player_id: number | null;
  assignee_name: string | null;
  cp: number | null;
}

export interface CpWorklistResponse {
  total: number;
  groups: ApartadoGroup[];
  xxl_total: number;
  xxl_items: XxlWorklistItem[];
  jira_base_url: string | null;
}
