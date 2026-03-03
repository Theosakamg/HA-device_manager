/**
 * Normalisation utilities for device function and firmware names.
 *
 * These helpers slugify free-text values coming from CSV imports (or manual
 * input) so they can be matched against known entity names.
 */
import { sanitizeSlug } from "./computed-fields";
import { DEVICE_FUNCTIONS, DEVICE_FIRMWARES } from "../types/device";

/* ------------------------------------------------------------------ */
/*  Function normalizer                                                */
/* ------------------------------------------------------------------ */

const ALLOWED_FUNCTIONS: ReadonlySet<string> = new Set(DEVICE_FUNCTIONS);

/**
 * Normalize a device function string to its canonical slug form.
 *
 * @param fn - Raw function name (e.g. "Button", "DoorBell").
 * @returns The normalized slug, or `null` if the input is empty/null.
 */
export function normalizeFunction(fn?: string | null): string | null {
  if (!fn && fn !== "") return null;
  const s = String(fn).trim().toLowerCase();
  if (ALLOWED_FUNCTIONS.has(s)) return s;
  return sanitizeSlug(s) || null;
}

/* ------------------------------------------------------------------ */
/*  Firmware normalizer                                                */
/* ------------------------------------------------------------------ */

const ALLOWED_FIRMWARES: ReadonlySet<string> = new Set(DEVICE_FIRMWARES);

/**
 * Normalize a firmware name to its canonical slug form.
 *
 * Handles common variants (e.g. "Embedded" → "embeded").
 *
 * @param fw - Raw firmware name (e.g. "Tasmota", "WLED").
 * @returns The normalized slug, or `null` if the input is empty/null.
 */
export function normalizeFirmware(fw?: string | null): string | null {
  if (!fw && fw !== "") return null;
  const s = String(fw).trim().toLowerCase();
  if (ALLOWED_FIRMWARES.has(s)) return s;
  // Handle common variant: "embedded" → "embeded"
  const alt = s.replace(/embedded/, "embeded");
  if (ALLOWED_FIRMWARES.has(alt)) return alt;
  return sanitizeSlug(s) || null;
}
