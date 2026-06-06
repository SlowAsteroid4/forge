/** Tipos que mapean las respuestas de /api/admin/cycles/* (UC-05) */

export interface CycleCandidate {
  player_id: number;
  display_name: string;
  area: string;
  sp_total: number;
  cp_total: number;
  subtasks_done: number;
  avg_m_calidad: number | null;
  metric_highlight: string;
}

export interface CycleKPIs {
  cp_done: number;
  sp_generated: number;
  subtasks_done: number;
  bugs_derived: number;
}

export interface TopPlayer {
  player_id: number;
  display_name: string;
  area: string;
  sp: number;
}

export interface CycleCloseSummary {
  cycle_id: number;
  cycle_name: string;
  cycle_status: string;
  kpis: CycleKPIs;
  top_players: TopPlayer[];
  can_close: boolean;
  blocking_errors: string[];
  warnings: string[];
}

export interface CloseRequest {
  mvp_player_id: number;
  mvp_reason: string;
}

export interface MvpEditRequest {
  new_mvp_player_id: number;
  reason: string;
}

export interface CycleCloseResponse {
  cycle_id: number;
  cycle_name: string;
  status: string;
  closed_at: string | null;
  mvp_player_id: number | null;
  mvp_reason: string | null;
  message: string;
}

export interface MvpHistoryItem {
  cycle_id: number;
  cycle_name: string;
  closed_at: string | null;
  mvp_player_id: number;
  mvp_display_name: string;
  mvp_area: string;
  mvp_reason: string | null;
}

export interface PlayerOption {
  id: number;
  display_name: string;
  area: string;
}
