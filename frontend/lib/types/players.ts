export type AreaEnum = "BE" | "FE" | "DESIGN" | "DB" | "QA" | "PO" | "PM";
export type EmploymentType = "internal" | "external";

export interface PlayerAdminItem {
  id: number;
  jira_account_id: string;
  display_name: string;
  email: string | null;
  area: AreaEnum;
  employment_type: EmploymentType;
  is_active: boolean;
  is_lead: boolean;
  monthly_salary: number | null;
  hourly_rate: number | null;
  monthly_hours_cap: number | null;
}

export interface PlayerAdminListResponse {
  players: PlayerAdminItem[];
  total: number;
}

export interface PlayerUpdateRequest {
  area?: AreaEnum;
  employment_type?: EmploymentType;
  is_active?: boolean;
  is_lead?: boolean;
  monthly_salary?: number | null;
  hourly_rate?: number | null;
  monthly_hours_cap?: number | null;
}

export interface PlayerAdminUpdateResponse {
  ok: boolean;
  message: string;
  player: PlayerAdminItem;
}
