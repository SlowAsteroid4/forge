/** Analytics types — aligned with backend/src/forge/schemas/analytics.py */

export type AnalyticsScope = "cycle" | "window" | "historical";
export type AnalyticsScopePartial = "cycle" | "window"; // for endpoints that don't support historical
export type GroupBy = "area" | "player";

// --- Throughput ---
export interface ThroughputPoint {
  cycle_id: number;
  cycle_name: string;
  iso_year: number;
  iso_week: number;
  start_date: string;
  end_date: string;
  status: string;
  done_count: number;
  total_cp: number;
}

export interface ThroughputResponse {
  cycles: ThroughputPoint[];
  total_cycles: number;
}

// --- CP by Area ---
export interface AreaBreakdown {
  area: string;
  done_count: number;
  total_cp: number;
}

export interface CpByAreaResponse {
  scope: string;
  cycle_id: number | null;
  areas: AreaBreakdown[];
}

// --- CP per Day by Dev ---
export interface DevCpPerDay {
  player_id: number;
  display_name: string;
  area: string;
  done_count: number;
  total_cp: number;
  biz_days: number;
  cp_per_day: number;
}

export interface CpPerDayResponse {
  scope: string;
  biz_days: number;
  devs: DevCpPerDay[];
}

// --- QA First-pass by Dev ---
export interface DevQaFirstPass {
  player_id: number;
  display_name: string;
  area: string;
  total: number;
  passed: number;
  first_pass_pct: number;
}

export interface QaFirstPassResponse {
  scope: string;
  devs: DevQaFirstPass[];
}

// --- Time in Status (buckets) ---
export interface TimeInStatusRow {
  group_key: string;
  display_name: string;
  area: string | null;
  done_count: number;
  dev_resp_h: number;
  qa_h: number;
  review_h: number;
  blocked_h: number;
  waiting_h: number;
  total_h: number;
}

export interface TimeInStatusResponse {
  scope: string;
  group_by: string;
  rows: TimeInStatusRow[];
  bucket_definitions: Record<string, string>;
}

// --- Time in Status Detail (raw Jira states) ---
export interface StatusDetailRow {
  group_key: string;
  display_name: string;
  area: string | null;
  done_count: number;
  total_h: number;
  by_status: Record<string, number>;
}

export interface TimeInStatusDetailResponse {
  scope: string;
  group_by: string;
  rows: StatusDetailRow[];
}
