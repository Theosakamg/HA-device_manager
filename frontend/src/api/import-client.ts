/**
 * API client for CSV import operations.
 */
import type { ImportResult } from "../types/device";
import { BaseClient } from "./base-client";

export class ImportClient extends BaseClient {
  /** Import devices from a CSV file. */
  async importCSV(file: File): Promise<ImportResult> {
    return this.upload<ImportResult>("/import", file);
  }
}
