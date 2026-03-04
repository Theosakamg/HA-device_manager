/**
 * Shared validation patterns and helpers used across the frontend.
 *
 * Centralises all regex constants to avoid duplication between
 * computed-fields.ts, device-table.ts, node-detail.ts, etc.
 */

/** Valid last-octet integer (0–255). */
export const IP_LAST_OCTET_REGEX = /^\d+$/;

/** Valid dotted partial prefix "A.B.C" (three octets). */
export const IP_PREFIX_REGEX = /^\d{1,3}\.\d{1,3}\.\d{1,3}$/;

/** Valid full dotted-quad IPv4 address "A.B.C.D". */
export const IPV4_REGEX = /^\d{1,3}(\.\d{1,3}){3}$/;

/** URL-safe slug: letters, digits, hyphens, underscores. */
export const SLUG_REGEX = /^[a-z0-9_-]+$/i;

/**
 * Returns true if the string is a valid http/https URL,
 * or if it is empty/undefined (optional field).
 */
export function isValidUrl(s?: string | null): boolean {
  if (!s || !s.trim()) return true;
  try {
    const u = new URL(s.trim());
    return u.protocol === "http:" || u.protocol === "https:";
  } catch {
    return false;
  }
}

/** Returns true if the slug matches the allowed pattern. */
export function isValidSlug(s: string): boolean {
  return SLUG_REGEX.test(s.trim());
}
