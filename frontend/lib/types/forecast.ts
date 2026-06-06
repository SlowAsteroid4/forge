/** Forecast types — aligned with backend/src/forge/schemas/forecast.py */

export interface AreaForecast {
  area: string;
  cp_done: number;
  cp_pending: number;
  n_cycles_data: number;
  velocity_avg: number;
  velocity_best: number;
  velocity_cons: number;
  weeks_optimistic: number;
  weeks_realistic: number;
  weeks_conservative: number;
  date_optimistic: string;
  date_realistic: string;
  date_conservative: string;
  preliminary: boolean;
}

export interface EpicForecastItem {
  epic_key: string;
  summary: string;
  project_code: string;
  status: string;
  cp_total: number;
  cp_done: number;
  cp_pending: number;
  pct_done: number;
  date_optimistic: string | null;
  date_realistic: string | null;
  date_conservative: string | null;
  preliminary: boolean;
  warning: string | null;
  blocked_count: number;
}

export interface EpicForecastDetail extends EpicForecastItem {
  areas: AreaForecast[];
}

export interface EpicForecastListResponse {
  epics: EpicForecastItem[];
  total: number;
  n_closed_cycles: number;
  window_size: number;
  calculated_at: string;
}
