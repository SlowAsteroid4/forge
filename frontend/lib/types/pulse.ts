// Zona de color JPDS por estado (paleta WP-07b). El backend la envía por fila.
export type PulseZone = "neutral" | "dev" | "review" | "qa" | "blocked" | "done";

// CAMBIO 1: franja de contadores por estado (orden de flujo)
export interface FlowCounter {
  key: string;
  label: string;
  count: number;
  raw_statuses: string[];
  zone: PulseZone;
}

// CAMBIO 2: cards por área
export interface AreaTask {
  jira_key: string;
  summary: string;
  status: string;
  zone: PulseZone;
  assignee_name: string | null;
  assignee_player_id: number | null;
  is_aggregate_team: boolean;
}

export interface AreaStatusGroup {
  status: string;
  zone: PulseZone;
  count: number;
  tasks: AreaTask[];
}

export interface AreaCard {
  area: string;
  total_active: number;
  by_status: AreaStatusGroup[];
}

// CAMBIO 3: drill-down de dev
export interface DevTask {
  jira_key: string;
  summary: string;
  status: string;
  zone: PulseZone;
  area: string;
  dias_en_estado: number;
}

export interface DevDrilldown {
  player_id: number;
  display_name: string;
  is_aggregate_team: boolean;
  area: string | null;
  total: number;
  tasks: DevTask[];
}

// Secciones conservadas
export interface BlockItem {
  jira_key: string;
  summary: string;
  area: string;
  assignee_name: string | null;
  assignee_player_id: number | null;
  horas_bloqueado: number;
  es_critico: boolean;
  block_reason: string | null;
}

export interface DayMovementItem {
  jira_key: string;
  summary: string;
  area: string;
  assignee_name: string | null;
  from_status: string;
  to_status: string;
  moved_at: string;
}

export interface AgingItem {
  jira_key: string;
  summary: string;
  area: string;
  status: string;
  assignee_name: string | null;
  assignee_player_id: number | null;
  dias_en_estado: number;
  edad_total_dias: number;
}

export interface ReadyQueueItem {
  jira_key: string;
  summary: string;
  area: string;
  cp: number | null;
  assignee_name: string | null;
  tiempo_en_ready_horas: number;
  priority: string | null;
}

export interface PulseSnapshot {
  generated_at: string;
  filters_applied: {
    areas: string[] | null;
    project_code: string | null;
    player_id: number | null;
  };
  flow_counters: FlowCounter[];
  area_cards: AreaCard[];
  blocks: BlockItem[];
  day_movements: DayMovementItem[];
  aging_critical: AgingItem[];
  ready_queue: ReadyQueueItem[];
}

export interface FlagForReviewResponse {
  jira_key: string;
  audit_log_id: number;
  message: string;
}
