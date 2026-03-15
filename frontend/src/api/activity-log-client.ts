/**
 * API client for activity log operations.
 */
import { BaseClient } from "./base-client";
import type {
  ActivityLogPage,
  ActivityLogFilters,
} from "../types/activity-log";

export class ActivityLogClient extends BaseClient {
  /** Fetch a paginated, filtered list of activity log entries. */
  async list(filters: ActivityLogFilters = {}): Promise<ActivityLogPage> {
    const params = new URLSearchParams();
    if (filters.dateFrom) params.set("date_from", filters.dateFrom);
    if (filters.dateTo) params.set("date_to", filters.dateTo);
    if (filters.eventType) params.set("event_type", filters.eventType);
    if (filters.entityType) params.set("entity_type", filters.entityType);
    if (filters.user) params.set("user", filters.user);
    if (filters.severity) params.set("severity", filters.severity);
    if (filters.page) params.set("page", String(filters.page));
    if (filters.pageSize) params.set("page_size", String(filters.pageSize));

    const qs = params.toString();
    return this.get<ActivityLogPage>(`/activity_log${qs ? `?${qs}` : ""}`);
  }

  /** Export all activity log entries as a file download. */
  async exportData(format: "csv" | "json"): Promise<void> {
    const url = `${this.baseUrl}/activity_log/export?format=${encodeURIComponent(format)}`;
    const headers = this.buildHeaders();
    const response = await fetch(url, {
      method: "GET",
      headers,
      credentials: "same-origin",
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.error || `Export failed: ${response.statusText}`);
    }

    const disposition = response.headers.get("Content-Disposition") || "";
    const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
    const filename = filenameMatch?.[1] || `activity_log.${format}`;

    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }

  /** Purge activity log entries older than N days. */
  async purge(
    olderThanDays: number
  ): Promise<{ success: boolean; deleted: number }> {
    return this.post<{ success: boolean; deleted: number }>(
      "/activity_log/purge",
      {
        older_than_days: olderThanDays,
      }
    );
  }
}
