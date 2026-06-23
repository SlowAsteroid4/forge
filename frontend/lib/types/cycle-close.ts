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

export interface IssueBreakdown {
  jira_key: string;
  title: string;
  cp: number | null;
  sp_final: number | null;
}

export interface AdjustmentLine {
  label: string;
  amount_sp: number; // ya viene firmado
}

export interface TopPlayer {
  player_id: number;
  display_name: string;
  area: string;
  sp: number;
  por_issue: IssueBreakdown[];
  ajustes_no_issue: AdjustmentLine[];
}

export interface BlockingError {
  type: string;
  message: string;
  issue_keys: string[];
}

export interface CycleCloseSummary {
  cycle_id: number;
  cycle_name: string;
  cycle_status: string;
  kpis: CycleKPIs;
  top_players: TopPlayer[];
  can_close: boolean;
  blocking_errors: BlockingError[];
  warnings: string[];
  jira_base_url: string | null;
}

export interface CycleRecalcResponse {
  cycle_id: number;
  recalculated: number;
  message: string;
  summary: CycleCloseSummary;
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
