export interface PlayerCostItem {
  player_id: number;
  display_name: string;
  area: string;
  employment_type: "internal" | "external";
  cp_total: number;
  sp_total: number;
  done_subtasks: number;
  cost_total: number | null;
  cost_per_cp: number | null;
  cost_per_sp: number | null;
  cost_not_captured: boolean;
  no_production: boolean;
  cost_note: string | null;
}

export interface AreaCostItem {
  area: string;
  players_active: number;
  cp_total: number;
  sp_total: number;
  done_subtasks: number;
  cost_total: number | null;
  cost_per_cp: number | null;
  cost_per_sp: number | null;
  delta_pct: number | null;
  players: PlayerCostItem[];
}

export interface AreaCostResponse {
  areas: AreaCostItem[];
  period: string;
  period_start: string;
  period_end: string;
  has_any_cost: boolean;
  total_cp: number;
  total_cost: number | null;
}

export interface IntExtComparisonItem {
  area: string;
  int_cost_per_cp: number | null;
  ext_cost_per_cp: number | null;
  int_players: number;
  ext_players: number;
  multiplier: number | null;
  insight: string;
}

export interface ComparisonResponse {
  comparisons: IntExtComparisonItem[];
  period: string;
  period_start: string;
  period_end: string;
}

export interface EvolutionPointItem {
  period_label: string;
  period_start: string;
  period_end: string;
  cp_total: number;
  cost_total: number | null;
  cost_per_cp: number | null;
}

export interface EvolutionResponse {
  points: EvolutionPointItem[];
  area: string | null;
}
