export interface Project {
  code: string;
  internal_name: string;
  arena_name: string;
  jira_prefix: string;
  is_active: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface ErrorResponse {
  error: string;
  message: string;
}
