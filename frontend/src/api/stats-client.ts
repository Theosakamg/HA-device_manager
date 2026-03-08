/**
 * API client for dashboard statistics.
 *
 * Fetches pre-aggregated counts from the backend so the UI never needs to
 * fetch the full device list just to draw KPI cards.
 */
import { BaseClient } from "./base-client";

export interface StatEntry {
  name: string;
  count: number;
}

export interface SettingsCounts {
  models: number;
  firmwares: number;
  functions: number;
}

export interface DashboardStats {
  buildings: number;
  floors: number;
  rooms: number;
  devices: number;
  byFirmware: StatEntry[];
  byModel: StatEntry[];
  settingsCounts: SettingsCounts;
}

export class StatsClient extends BaseClient {
  async getStats(): Promise<DashboardStats> {
    return this.get<DashboardStats>("/stats");
  }
}
