export interface Cycle {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  days_elapsed: number;
  days_total: number;
  progress_pct: number;
}

export interface KpiValueFull {
  value: number;
  previous_value?: number | null;
  delta_pct?: number | null;
}

export interface DashboardKpis {
  cp_done: KpiValueFull;
  cp_pending: number;
  sp_total: number;
  bugs_derived: number;
}

export type DevStatus = "productive" | "wip_high" | "blocked" | "inactive";

export interface AreaProgress {
  area: string;
  cp_done: number;
  cp_total: number;
  progress_pct: number;
  active_devs: number;
  has_wip_bottleneck: boolean;
}

export interface PlayerStatus {
  player_id: number;
  display_name: string;
  avatar_code: string | null;
  area: string;
  active_subtasks: number;
  done_subtasks: number;
  sp_sprint: number;
  status: DevStatus;
}

export interface DashboardAlert {
  alert_type: string;
  severity: string;
  subtask_key?: string | null;
  player_id?: number | null;
  message: string;
}

export interface AvailableProject {
  code: string;
  internal_name: string;
  jira_prefix: string;
}

export interface AvailableCycle {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  status: string;
}

export interface DashboardResponse {
  cycle: Cycle | null;
  no_cycle_message?: string | null;
  kpis: DashboardKpis;
  area_progress: AreaProgress[];
  player_status: PlayerStatus[];
  alerts: DashboardAlert[];
  available_projects: AvailableProject[];
  available_cycles: AvailableCycle[];
  last_synced_at: string | null;
}
