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

export interface DeploymentStats {
  total: number;
  success: number;
  fail: number;
}

export interface DeploymentByGroup {
  name: string;
  total: number;
  success: number;
  fail: number;
}

export interface DashboardStats {
  buildings: number;
  floors: number;
  rooms: number;
  devices: number;
  byFirmware: StatEntry[];
  byModel: StatEntry[];
  settingsCounts: SettingsCounts;
  deployment: DeploymentStats;
  deploymentByFirmware: DeploymentByGroup[];
  deploymentByModel: DeploymentByGroup[];
}

export class StatsClient extends BaseClient {
  async getStats(): Promise<DashboardStats> {
    return this.get<DashboardStats>("/stats");
  }
}
