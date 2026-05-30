/** Tipos que mapean las respuestas de /api/cp-approvals/* */

export interface CpApprovalPendingItem {
  jira_key: string;
  summary: string;
  area: string;
  project_code: string | null;
  assignee_player_id: number | null;
  complexity_size: string | null;
  cp: number | null;
  cp_proposed_at: string | null;
  cp_proposed_by: number | null;
  waiting_days: number;
  is_overdue: boolean;
  cp_rejection_reason: string | null;
}

export interface CpApprovalDetail extends CpApprovalPendingItem {
  status: string;
  cycle_id: number | null;
  cp_approved_at: string | null;
  cp_approved_by: number | null;
  cp_approval_required: boolean;
  cp_modified_post_approval: boolean;
}

export interface XxlItem {
  jira_key: string;
  summary: string;
  area: string;
  project_code: string | null;
  assignee_player_id: number | null;
  cp: number | null;
}

export interface CpApprovalListResponse {
  total: number;
  items: CpApprovalPendingItem[];
}

export interface XxlListResponse {
  total: number;
  items: XxlItem[];
}
