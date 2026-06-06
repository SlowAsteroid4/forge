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

// --- WP-17a: Quality, vs ciclo anterior, canónico ---

export interface CycleBrief {
  cycle_id: number;
  name: string;
  iso_year: number;
  iso_week: number;
  status: string;
}

export interface DeltaMetric {
  current: number;
  previous: number | null;
  delta_abs: number | null;
  delta_pct: number | null;
}

export interface QualitySummaryResponse {
  reference_cycle: CycleBrief | null;
  previous_cycle: CycleBrief | null;
  tested: DeltaMetric;
  pending: DeltaMetric;
  avg_qa_hours: DeltaMetric;
}

export interface DevQaVsPrevious {
  player_id: number;
  display_name: string;
  area: string;
  total: number;
  passed: number;
  first_pass_pct: number;
  previous_pct: number | null;
  delta_pts: number | null;
}

export interface QaFirstPassVsPreviousResponse {
  reference_cycle: CycleBrief | null;
  previous_cycle: CycleBrief | null;
  devs: DevQaVsPrevious[];
}

/** Los 9 estados canónicos del Manifiesto JPDS. */
export type CanonicalStatus =
  | "Backlog"
  | "Ready"
  | "In Progress"
  | "In Review"
  | "In QA"
  | "Waiting"
  | "Blocked"
  | "Done"
  | "Cancelled";

export interface CanonicalTimeRow {
  group_key: string;
  display_name: string;
  area: string | null;
  done_count: number;
  by_canonical: Record<string, number>;
  total_h: number;
}

export interface CanonicalTimeResponse {
  scope: string;
  group_by: string;
  area_filter: string | null;
  rows: CanonicalTimeRow[];
}
