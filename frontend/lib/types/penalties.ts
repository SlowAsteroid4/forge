/** Tipos para UC-06: penalizaciones manuales + apelaciones */

export interface PenaltyListItem {
  id: number;
  subtask_key: string | null;
  subtask_summary: string | null;
  cycle_id: number | null;
  player_id: number | null;
  player_name: string | null;
  adjustment_type: string;
  catalog_code: string | null;
  amount_sp: number;
  reason: string;
  applied_by: number;
  applied_by_name: string | null;
  applied_at: string | null;
  is_appealed: boolean;
  appeal_resolution: "upheld" | "reversed" | "reduced" | null;
  appeal_resolved_by: number | null;
  appeal_resolved_by_name: string | null;
  appeal_resolved_at: string | null;
  appeal_notes: string | null;
  sp_final_current: number | null;
}

export interface PenaltyListResponse {
  total: number;
  page: number;
  page_size: number;
  items: PenaltyListItem[];
}

export interface PendingAppealsResponse {
  total: number;
  items: PenaltyListItem[];
}

export interface DebuffCatalogItem {
  code: string;
  narrative_name: string;
  trigger_description: string;
  penalty_type: "flat" | "percentage";
  value: number;
  is_appealable: boolean;
  icon_code: string | null;
  is_auto: boolean;
}

export interface DebuffCatalogResponse {
  total: number;
  items: DebuffCatalogItem[];
}

export interface ApplyPenaltyRequest {
  subtask_key: string;
  reason: string;
  catalog_code?: string;
  custom_sp?: number;
}

export interface ReversePenaltyRequest {
  reason: string;
  partial_new_value?: number;
}

export interface ResolveAppealRequest {
  resolution: "upheld" | "reversed" | "reduced";
  notes: string;
  reduced_value?: number;
}

export interface PenaltyActionResponse {
  ok: boolean;
  message: string;
  adjustment_id: number;
  subtask_key?: string;
  sp_final?: number;
}
