/**
 * In-UI documentation registry.
 *
 * Maps dot-notation keys (e.g. "settings.models.overview") to structured doc
 * content per language. All markdown files are bundled at build time via
 * Vite's `?raw` imports — no runtime fetches needed.
 *
 * Each markdown file must start with a YAML frontmatter block:
 * ```markdown
 * ---
 * description: "Short summary shown in the collapsed header"
 * ---
 *
 * Full body rendered in the collapsible section.
 * ```
 *
 * ## Adding a new doc page
 * 1. Create `src/docs/<context>/<entity>/<page>.<lang>.md` with frontmatter
 * 2. Import the file below with `?raw`
 * 3. Add an entry to `DOC_REGISTRY`
 *
 * ## Usage
 * ```ts
 * import { getDoc } from "../../utils/doc-registry";
 *
 * const doc = getDoc("settings.models.overview"); // lang auto-detected
 * // doc.summary → collapsed header text (inline markdown)
 * // doc.body    → collapsible body (full markdown)
 * ```
 */

import { i18n } from "../i18n";
import { parseFrontmatter, type DocContent } from "./frontmatter";

// ---------------------------------------------------------------------------
// Raw markdown imports (bundled at build time by Vite)
// ---------------------------------------------------------------------------

import settingsModelsOverviewEn from "../docs/settings/models/overview.en.md?raw";
import settingsModelsOverviewFr from "../docs/settings/models/overview.fr.md?raw";

import settingsFirmwaresOverviewEn from "../docs/settings/firmwares/overview.en.md?raw";
import settingsFirmwaresOverviewFr from "../docs/settings/firmwares/overview.fr.md?raw";

import settingsFunctionsOverviewEn from "../docs/settings/functions/overview.en.md?raw";
import settingsFunctionsOverviewFr from "../docs/settings/functions/overview.fr.md?raw";

import settingsOverviewEn from "../docs/settings/overview.en.md?raw";
import settingsOverviewFr from "../docs/settings/overview.fr.md?raw";

import maintenanceOverviewEn from "../docs/maintenance/overview.en.md?raw";
import maintenanceOverviewFr from "../docs/maintenance/overview.fr.md?raw";

import maintenanceSettingsOverviewEn from "../docs/maintenance/settings/overview.en.md?raw";
import maintenanceSettingsOverviewFr from "../docs/maintenance/settings/overview.fr.md?raw";

import maintenanceExportOverviewEn from "../docs/maintenance/export/overview.en.md?raw";
import maintenanceExportOverviewFr from "../docs/maintenance/export/overview.fr.md?raw";

import maintenanceImportOverviewEn from "../docs/maintenance/import/overview.en.md?raw";
import maintenanceImportOverviewFr from "../docs/maintenance/import/overview.fr.md?raw";

import maintenanceScanOverviewEn from "../docs/maintenance/scan/overview.en.md?raw";
import maintenanceScanOverviewFr from "../docs/maintenance/scan/overview.fr.md?raw";

import maintenanceDangerOverviewEn from "../docs/maintenance/danger/overview.en.md?raw";
import maintenanceDangerOverviewFr from "../docs/maintenance/danger/overview.fr.md?raw";

import hierarchyBuildingOverviewEn from "../docs/hierarchy/building/overview.en.md?raw";
import hierarchyBuildingOverviewFr from "../docs/hierarchy/building/overview.fr.md?raw";

import hierarchyFloorOverviewEn from "../docs/hierarchy/floor/overview.en.md?raw";
import hierarchyFloorOverviewFr from "../docs/hierarchy/floor/overview.fr.md?raw";

import hierarchyRoomOverviewEn from "../docs/hierarchy/room/overview.en.md?raw";
import hierarchyRoomOverviewFr from "../docs/hierarchy/room/overview.fr.md?raw";

import hierarchyRoomDeviceListEn from "../docs/hierarchy/room/device_list.en.md?raw";
import hierarchyRoomDeviceListFr from "../docs/hierarchy/room/device_list.fr.md?raw";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Language-keyed raw markdown variants of a single doc page. */
type DocVariants = {
  en: string;
  [lang: string]: string;
};

/** Full registry: dot-notation key → language variants. */
type DocRegistry = Record<string, DocVariants>;

export type { DocContent };

// ---------------------------------------------------------------------------
// Registry
// ---------------------------------------------------------------------------

/**
 * Central map of all in-UI documentation pages.
 *
 * Key convention: `<context>.<entity>.<page>`
 *   - context : top-level feature area (e.g. "settings", "devices", "deploy")
 *   - entity  : specific sub-section  (e.g. "models", "firmwares", "functions")
 *   - page    : content variant       (e.g. "overview", "faq", "troubleshoot")
 */
const DOC_REGISTRY: DocRegistry = {
  "settings.overview": {
    en: settingsOverviewEn,
    fr: settingsOverviewFr,
  },
  "settings.models.overview": {
    en: settingsModelsOverviewEn,
    fr: settingsModelsOverviewFr,
  },
  "settings.firmwares.overview": {
    en: settingsFirmwaresOverviewEn,
    fr: settingsFirmwaresOverviewFr,
  },
  "settings.functions.overview": {
    en: settingsFunctionsOverviewEn,
    fr: settingsFunctionsOverviewFr,
  },
  "maintenance.overview": {
    en: maintenanceOverviewEn,
    fr: maintenanceOverviewFr,
  },
  "maintenance.settings.overview": {
    en: maintenanceSettingsOverviewEn,
    fr: maintenanceSettingsOverviewFr,
  },
  "maintenance.export.overview": {
    en: maintenanceExportOverviewEn,
    fr: maintenanceExportOverviewFr,
  },
  "maintenance.import.overview": {
    en: maintenanceImportOverviewEn,
    fr: maintenanceImportOverviewFr,
  },
  "maintenance.scan.overview": {
    en: maintenanceScanOverviewEn,
    fr: maintenanceScanOverviewFr,
  },
  "maintenance.danger.overview": {
    en: maintenanceDangerOverviewEn,
    fr: maintenanceDangerOverviewFr,
  },
  "hierarchy.building.overview": {
    en: hierarchyBuildingOverviewEn,
    fr: hierarchyBuildingOverviewFr,
  },
  "hierarchy.floor.overview": {
    en: hierarchyFloorOverviewEn,
    fr: hierarchyFloorOverviewFr,
  },
  "hierarchy.room.overview": {
    en: hierarchyRoomOverviewEn,
    fr: hierarchyRoomOverviewFr,
  },
  "hierarchy.room.device_list": {
    en: hierarchyRoomDeviceListEn,
    fr: hierarchyRoomDeviceListFr,
  },
};

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Return the parsed doc content for the given key in the current UI language.
 *
 * The returned object contains:
 * - `summary` — short description from the frontmatter, used in the collapsed
 *   header (supports inline markdown)
 * - `body` — full markdown body rendered in the collapsible section
 *
 * Falls back to English when the current language is not available for a key.
 * Returns `undefined` (with a console warning) when the key is unknown.
 *
 * @param key  - Dot-notation key, e.g. `"settings.models.overview"`
 * @param lang - Override language (defaults to the current i18n language)
 */
export function getDoc(key: string, lang?: string): DocContent | undefined {
  const entry = DOC_REGISTRY[key];
  if (!entry) {
    console.warn(`[doc-registry] Unknown doc key: "${key}"`);
    return undefined;
  }
  const resolvedLang = lang ?? i18n.getCurrentLanguage();
  const raw = entry[resolvedLang] ?? entry["en"] ?? "";
  return parseFrontmatter(raw);
}

/**
 * Return all registered doc keys.
 * Useful for dev tooling / inspection.
 */
export function listDocKeys(): string[] {
  return Object.keys(DOC_REGISTRY);
}
