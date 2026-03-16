/**
 * Computed field calculations for DmDevice.
 *
 * These fields are derived from the device's base data and its hierarchical
 * context (room, level, home). They are NOT stored in the database.
 */
import type { DmDevice, ComputedDeviceFields } from "../types/device";
import { getSettings } from "../api/settings-client";
import { toSlug } from "./slug";
import { IP_LAST_OCTET_REGEX, IP_PREFIX_REGEX, IPV4_REGEX } from "./validators";

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
  if (IP_LAST_OCTET_REGEX.test(s) && Number(s) >= 0 && Number(s) <= 255) {
    const { ip_prefix } = getSettings();
    // Validate ip_prefix is a valid partial IP (e.g. "192.168.0")
    if (!IP_PREFIX_REGEX.test(ip_prefix)) return null;
    return `http://${ip_prefix}.${s}`;
  }
  // Full dotted-quad IPv4
  if (IPV4_REGEX.test(s)) {
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
  const { dns_suffix } = getSettings();

  const buildingSlug = sanitizeSlug(device.building?.slug);
  const floorSlug = sanitizeSlug(device.floor?.slug) || "l0";
  const roomSlug = sanitizeSlug(device.room?.slug);
  const functionName = sanitizeSlug(device.refs?.functionName);
  const posSlug = sanitizeSlug(device.positionSlug);

  // Hostname: {building}_{floor}_{room}_{function}_{position}
  // Format changed to include building_slug (matching backend)
  const hostParts: string[] = [];
  if (buildingSlug) hostParts.push(buildingSlug);
  if (floorSlug) hostParts.push(floorSlug);
  if (roomSlug) hostParts.push(roomSlug);
  if (functionName) hostParts.push(functionName);
  if (posSlug) hostParts.push(posSlug);
  const hostname = hostParts.length > 0 ? hostParts.join("_") : null;

  // MQTT topic: {building}/{floor}/{room}/{function}/{position}
  // Format changed to use building_slug instead of mqtt_topic_prefix (matching backend)
  const mqttTopic =
    buildingSlug && roomSlug && functionName && posSlug
      ? `${buildingSlug}/${floorSlug}/${roomSlug}/${functionName}/${posSlug}`
      : null;

  // FQDN: {hostname}.{dns_suffix}
  const fqdn = hostname ? `${hostname}.${dns_suffix}` : null;

  // Link: HTTP URL from IP
  const link = buildHttpFromIp(device.ip);

  // Count topic: hostname length
  const countTopic = hostname ? hostname.length : null;

  return { link, mqttTopic, hostname, fqdn, countTopic };
}

/**
 * Compute the MQTT topic and HA entity_id for a hierarchy node
 * (building, floor, or room) based on the ordered list of slugs from root
 * to the current node.
 *
 * @param slugs - Ordered slugs from building down to the current node,
 *   e.g. ["home", "l1", "kitchen"] for a room.
 * @returns An object with `mqttTopic` and `haEntityId`.
 */
export function computeHierarchyPrefixes(slugs: string[]): {
  mqttTopic: string;
  haEntityId: string;
} {
  const path = slugs.filter(Boolean);
  const mqttTopic = path.length > 0 ? `${path.join("/")}/#` : "";
  const haEntityId = path.length > 0 ? `{domain}.${path.join("_")}` : "";
  return { mqttTopic, haEntityId };
}

/**
 * Return a short human-readable label for a device.
 *
 * Uses the server-computed `displayName` when available, otherwise builds the
 * label client-side as "Building > Floor > Room > Function > Position".
 * Falls back to the MAC address when no hierarchy data is present.
 *
 * @param device - The device object (may include transient joined fields).
 * @returns A concise identifier string, never empty.
 */
export function deviceLabel(device: Partial<DmDevice>): string {
  if (device.displayName) return device.displayName;

  const parts = [
    device.building?.name,
    device.floor?.slug,
    device.room?.slug,
    device.refs?.functionName,
    device.positionSlug,
  ].filter(Boolean);

  return parts.length > 0 ? parts.join(" > ") : (device.mac ?? "—");
}
