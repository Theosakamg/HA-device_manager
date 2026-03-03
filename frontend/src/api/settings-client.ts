/**
 * API client for application settings.
 */
import { BaseClient } from "./base-client";

/** Settings key/value map returned by the API. */
export interface AppSettings {
  dns_suffix: string;
  ip_prefix: string;
  mqtt_topic_prefix: string;
  default_home_name: string;
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
      default_home_name: "Home",
    }
  );
}

/** Force-refresh the cache after a save. */
export async function refreshSettings(): Promise<AppSettings> {
  return loadSettings();
}
