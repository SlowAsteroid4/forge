/** Tipos que mapean las respuestas de /api/admin/months/* (UC-17) */

export interface MonthlyCandidate {
  player_id: number;
  display_name: string;
  area: string;
  mvp_cycles: string[];
  mvp_cycle_ids: number[];
  sp_total_month: number;
  cp_total_month: number;
  subtasks_done_month: number;
  avg_m_calidad: number | null;
  metric_highlight: string;
}

export interface MonthCycleInfo {
  cycle_id: number;
  name: string;
  status: string;
  mvp_player_id: number | null;
}

export interface MonthKPIs {
  cp_done: number;
  sp_generated: number;
  subtasks_done: number;
  cycles_total: number;
  cycles_closed_or_archived: number;
}

export interface MonthCloseSummary {
  year: number;
  month: number;
  period_label: string;
  cycles: MonthCycleInfo[];
  kpis: MonthKPIs;
  candidates: MonthlyCandidate[];
  already_closed: boolean;
  can_close: boolean;
  blocking_errors: string[];
  warnings: string[];
}

export interface MonthCloseRequest {
  mvp_player_id: number;
  reason: string;
}

export interface MonthlyMvpEditRequest {
  new_player_id: number;
  reason: string;
}

export interface MonthCloseResponse {
  period_label: string;
  player_id: number;
  display_name: string;
  sp_awarded: number;
  ach04_unlocked: boolean;
  message: string;
}

export interface MonthlyMvpHistoryItem {
  id: number;
  period_label: string;
  year: number;
  month: number;
  player_id: number;
  display_name: string;
  area: string | null;
  reason: string | null;
  sp_reward: number;
  assigned_at: string;
  assigned_by_name: string;
  source_cycle_ids: number[];
}
