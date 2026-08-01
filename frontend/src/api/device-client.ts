/**
 * API client for DmDevice CRUD operations.
 */
import type { DmDevice } from "../types/device";
import { CrudClient } from "./crud-client";

export class DeviceClient extends CrudClient<DmDevice> {
  constructor() {
    super("/devices");
  }

  /** Get all devices, optionally filtered by room. */
  override async getAll(roomId?: number | string): Promise<DmDevice[]> {
    const query =
      roomId !== undefined && roomId !== ""
        ? `?room_id=${encodeURIComponent(String(roomId))}`
        : "";
    return super.getAll(query);
  }

  /** Trigger deployment for a specific set of devices by MAC. */
  async deployBatch(macs: string[]): Promise<{ result: string }> {
    return this.post<{ result: string }>("/deploy", { macs });
  }

  // --- Tasmota runtime operations -----------------------------------------

  /** Restart a single Tasmota device (HTTP by default, MQTT optional). */
  async tasmotaRestart(
    mac: string,
    useMqtt = false
  ): Promise<{ mac: string; transport: string; ok: boolean }> {
    return this.post("/tasmota/restart", { mac, use_mqtt: useMqtt });
  }

  /** Trigger an OTA upgrade on a single Tasmota device. */
  async tasmotaUpgrade(
    mac: string,
    useMqtt = false
  ): Promise<{ mac: string; transport: string; ok: boolean }> {
    return this.post("/tasmota/upgrade", { mac, use_mqtt: useMqtt });
  }

  /** Query the full status of a single Tasmota device. */
  async tasmotaStatus(mac: string): Promise<{
    mac: string;
    online: boolean;
    status: Record<string, unknown>;
  }> {
    return this.post("/tasmota/status", { mac });
  }

  /** Switch the active WiFi AP of a single Tasmota device. */
  async tasmotaSwitchAp(
    mac: string,
    apId = 1
  ): Promise<{ mac: string; apId: number; ok: boolean }> {
    return this.post("/tasmota/switch-ap", { mac, ap_id: apId });
  }

  /** Ping every (or a filtered subset of) device and report which are offline. */
  async tasmotaCheckUnavailable(
    macs?: string[]
  ): Promise<{ checked: number; online: string[]; offline: string[] }> {
    return this.post("/tasmota/check-unavailable", { macs });
  }

  /** Switch the active AP on every (or filtered) device. */
  async tasmotaForceAp(
    apId = 1,
    macs?: string[]
  ): Promise<{
    total: number;
    switched: string[];
    failed: string[];
    ssid: string;
  }> {
    return this.post("/tasmota/force-ap", { ap_id: apId, macs });
  }

  /** Trigger OTA upgrade only on devices older than a target version. */
  async tasmotaUpdateFirmware(
    version: string,
    macs?: string[]
  ): Promise<{
    total: number;
    upgraded: string[];
    skipped: string[];
    failed: string[];
  }> {
    return this.post("/tasmota/update-firmware", { version, macs });
  }

  /** Restart a selected set of Tasmota devices (batch). */
  async tasmotaRestartBatch(
    macs: string[],
    useMqtt = false
  ): Promise<{ total: number; restarted: string[]; failed: string[] }> {
    return this.post("/tasmota/restart-batch", { macs, use_mqtt: useMqtt });
  }

  /** Trigger an unconditional OTA upgrade on a selected set of devices (batch). */
  async tasmotaUpgradeBatch(
    macs: string[],
    useMqtt = false
  ): Promise<{ total: number; upgraded: string[]; failed: string[] }> {
    return this.post("/tasmota/upgrade-batch", { macs, use_mqtt: useMqtt });
  }
}
