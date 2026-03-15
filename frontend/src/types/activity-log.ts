/**
 * Activity log entity interfaces.
 */
import type { BaseEntity } from "./base";

export type ActivityLogEventType = "config_change" | "action";
export type ActivityLogSeverity = "info" | "warning" | "error";

export interface ActivityLogEntry extends BaseEntity {
  timestamp: string;
  user: string;
  eventType: ActivityLogEventType;
  entityType: string;
  entityId?: number | null;
  message: string;
  result?: string | null;
  severity: ActivityLogSeverity;
}

export interface ActivityLogPage {
  items: ActivityLogEntry[];
  total: number;
  page: number;
  pageSize: number;
  pages: number;
}

export interface ActivityLogFilters {
  dateFrom?: string;
  dateTo?: string;
  eventType?: ActivityLogEventType | "";
  entityType?: string;
  user?: string;
  severity?: ActivityLogSeverity | "";
  page?: number;
  pageSize?: number;
}
