/**
 * Computed field calculations for DmDevice.
 *
 * These fields are derived from the device's base data and its hierarchical
 * context (room, level, home). They are NOT stored in the database.
 */
import type { DmDevice, ComputedDeviceFields } from "../types/device";
import { getSettings } from "../api/settings-client";
import { toSlug } from "./slug";

// Re-export DmDevice alias so callers migrating from old types can use it.
export type { DmDevice, ComputedDeviceFields };

/**
 * Sanitize a string into a URL-safe slug.
 *
 * @param value - The string to slugify.
 * @returns A lowercase slug or empty string.
 */
export function sanitizeSlug(value?: string | null): string {
  if (!value) return "";
  return toSlug(value);
}

/**
 * Build an HTTP URL from an IP address or numeric last octet.
 *
 * @param ip - The IP string (full dotted or numeric last octet).
 * @returns The HTTP URL or null.
 */
export function buildHttpFromIp(ip?: string | null): string | null {
  if (!ip) return null;
  const s = String(ip).trim();
  // Numeric-only: last octet, prepend ip_prefix
  if (/^\d+$/.test(s) && Number(s) >= 0 && Number(s) <= 255) {
    const { ip_prefix } = getSettings();
    // Validate ip_prefix is a valid partial IP (e.g. "192.168.0")
    if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(ip_prefix)) return null;
    return `http://${ip_prefix}.${s}`;
  }
  // Full dotted-quad IPv4
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(s)) {
    return `http://${s}`;
  }
  // Reject everything else (arbitrary URLs, javascript:, etc.)
  return null;
}

/**
 * Compute all derived fields for a device.
 *
 * @param device - The device (must include transient joined fields like
 *   roomSlug, floorSlug, functionName for meaningful results).
 * @returns The computed fields object.
 */
export function computeDerivedFields(
  device: Partial<DmDevice>
): ComputedDeviceFields {
  const { dns_suffix, mqtt_topic_prefix } = getSettings();

  const floorSlug = sanitizeSlug(device.floorSlug) || "l0";
  const roomSlug = sanitizeSlug(device.roomSlug);
  const functionName = sanitizeSlug(device.functionName);
  const posSlug = sanitizeSlug(device.positionSlug);

  // Hostname: l{floor}_{roomSlug}_{function}_{positionSlug}
  const hostParts: string[] = [];
  if (floorSlug) hostParts.push(floorSlug);
  if (roomSlug) hostParts.push(roomSlug);
  if (functionName) hostParts.push(functionName);
  if (posSlug) hostParts.push(posSlug);
  const hostname = hostParts.length > 0 ? hostParts.join("_") : null;

  // MQTT topic: {mqtt_prefix}/{floorSlug}/{roomSlug}/{function}/{positionSlug}
  const mqttTopic =
    roomSlug && functionName && posSlug
      ? `${mqtt_topic_prefix}/${floorSlug}/${roomSlug}/${functionName}/${posSlug}`
      : null;

  // FQDN: {hostname}.{dns_suffix}
  const fqdn = hostname ? `${hostname}.${dns_suffix}` : null;

  // Link: HTTP URL from IP
  const link = buildHttpFromIp(device.ip);

  // Count topic: hostname length
  const countTopic = hostname ? hostname.length : null;

  return { link, mqttTopic, hostname, fqdn, countTopic };
}
