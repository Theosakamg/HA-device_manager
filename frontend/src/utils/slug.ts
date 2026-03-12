/**
 * Slug utility functions.
 */

/**
 * Convert a string to a URL-safe slug.
 *
 * @param value - The string to slugify.
 * @returns A lowercase slug.
 */
export function toSlug(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9\-_.]/g, "");
}

/**
 * Convert a slug back to Title Case for display.
 *
 * @param slug - The slug to titleize.
 * @returns A title-cased string.
 */
export function toTitle(slug: string): string {
  if (!slug) return "";
  return slug.replace(/[-_]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
