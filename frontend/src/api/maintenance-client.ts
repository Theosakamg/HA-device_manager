/**
 * API client for maintenance operations.
 */
import { BaseClient } from "./base-client";

export interface CleanDBResult {
  success: boolean;
  deleted: Record<string, number>;
}

export type ExportFormat = "csv" | "json" | "yaml";

export class MaintenanceClient extends BaseClient {
  /** Wipe all data from the database. */
  async cleanDB(confirmation: string): Promise<CleanDBResult> {
    return this.post<CleanDBResult>("/maintenance/clean-db", { confirmation });
  }

  /** Export all devices in the given format as a file download. */
  async exportData(format: ExportFormat): Promise<void> {
    // Runtime validation of format
    const allowedFormats: ExportFormat[] = ["csv", "json", "yaml"];
    if (!allowedFormats.includes(format)) {
      throw new Error(`Invalid export format: ${format}`);
    }
    const url = `${this.baseUrl}/export?format=${encodeURIComponent(format)}`;
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

    // Extract filename from Content-Disposition or generate one
    const disposition = response.headers.get("Content-Disposition") || "";
    const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
    const filename = filenameMatch?.[1] || `devices.${format}`;

    // Download the blob
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
  }
}
