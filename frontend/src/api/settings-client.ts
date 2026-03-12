/**
 * API client for application settings.
 */
import { BaseClient } from "./base-client";

/** Settings key/value map returned by the API. */
export interface AppSettings {
  // Application
  dns_suffix: string;
  ip_prefix: string;
  mqtt_topic_prefix: string;
  default_building_name: string;
  // Provisioning: network scan
  scan_ssh_key_file: string;
  scan_ssh_user: string;
  scan_ssh_host: string;
  scan_script_content: string;
  // Provisioning: device access
  device_pass: string;
  // Provisioning: NTP
  ntp_server1: string;
  // Provisioning: WiFi
  wifi1_ssid: string;
  wifi1_password: string;
  wifi2_ssid: string;
  wifi2_password: string;
  // Provisioning: MQTT bus
  bus_host: string;
  bus_port: string;
  bus_username: string;
  bus_password: string;
  // Provisioning: Zigbee bridge
  bridge_host: string;
  bridge_devices_config_path: string;
}

export class SettingsClient extends BaseClient {
  /** Fetch all settings. */
  async getAll(): Promise<AppSettings> {
    // Settings use snake_case keys on both sides (they are domain keys, not column names)
    const response = await fetch(`${this.baseUrl}/settings`, {
      method: "GET",
      headers: this.buildHeaders("application/json"),
      credentials: "same-origin",
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(
        err.error || `Failed to load settings: ${response.statusText}`
      );
    }
    return response.json();
  }

  /** Update one or more settings. Returns the full settings after update. */
  async save(data: Partial<AppSettings>): Promise<AppSettings> {
    const response = await fetch(`${this.baseUrl}/settings`, {
      method: "PUT",
      headers: this.buildHeaders("application/json"),
      credentials: "same-origin",
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(
        err.error || `Failed to save settings: ${response.statusText}`
      );
    }
    return response.json();
  }

  /** Upload a SSH private key file. Returns the stored absolute path. */
  async uploadSshKey(
    file: File
  ): Promise<{ success: boolean; path: string; filename: string }> {
    return this.upload("/ssh-key/upload", file, "file");
  }
}

/**
 * Singleton settings cache.
 *
 * Call ``loadSettings()`` once at startup, then use ``getSettings()``
 * synchronously wherever needed (computed-fields, device-table, etc.).
 */
let _cached: AppSettings | null = null;
const _client = new SettingsClient();

/** Load settings from the API (call once at app init). */
export async function loadSettings(): Promise<AppSettings> {
  _cached = await _client.getAll();
  return _cached;
}

/** Return cached settings (falls back to sensible defaults if not yet loaded). */
export function getSettings(): AppSettings {
  return (
    _cached ?? {
      dns_suffix: "domo.local",
      ip_prefix: "192.168.0",
      mqtt_topic_prefix: "home",
      default_building_name: "Building",
      scan_ssh_key_file: "",
      scan_ssh_user: "root",
      scan_ssh_host: "",
      scan_script_content: "",
      device_pass: "",
      ntp_server1: "pool.ntp.org",
      wifi1_ssid: "",
      wifi1_password: "",
      wifi2_ssid: "",
      wifi2_password: "",
      bus_host: "bus",
      bus_port: "1883",
      bus_username: "admin",
      bus_password: "",
      bridge_host: "",
      bridge_devices_config_path: "/home/pi/zigbee2mqtt/data/devices.yaml",
    }
  );
}

/** Force-refresh the cache. If data is provided, use it directly; otherwise fetch from API. */
export async function refreshSettings(
  data?: AppSettings
): Promise<AppSettings> {
  if (data) {
    _cached = data;
    return data;
  }
  return loadSettings();
}
