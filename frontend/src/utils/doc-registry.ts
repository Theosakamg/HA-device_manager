/**
 * In-UI documentation registry.
 *
 * Maps dot-notation keys (e.g. "settings.models.overview") to structured doc
 * content per language. All markdown files under `src/docs/` are discovered
 * and bundled automatically at build time via Vite's `import.meta.glob` —
 * no manual registration or runtime fetches needed.
 *
 * ## File naming convention
 * `src/docs/<context>/[entity/]<page>.<lang>.md`
 *
 * The path maps directly to the registry key:
 * - `docs/settings/models/overview.en.md` → key `"settings.models.overview"`, lang `"en"`
 * - `docs/settings/overview.fr.md`        → key `"settings.overview"`,         lang `"fr"`
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
 * 1. Create `src/docs/<context>/[entity/]<page>.<lang>.md` with frontmatter.
 * 2. That's it — the file is picked up automatically on the next build.
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
// Auto-discovery via Vite glob import (bundled at build time)
// ---------------------------------------------------------------------------

const _rawDocs = import.meta.glob("../docs/**/*.md", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

/**
 * Derives the dot-notation registry key and language code from a glob path.
 *
 * "../docs/settings/models/overview.en.md" → { key: "settings.models.overview", lang: "en" }
 * "../docs/settings/overview.fr.md"        → { key: "settings.overview",         lang: "fr" }
 */
function _pathToKeyAndLang(
  path: string,
): { key: string; lang: string } | null {
  const inner = path.replace(/^\.\.\/docs\//, "").replace(/\.md$/, "");
  const segments = inner.split("/");
  const lastSegment = segments[segments.length - 1];
  const dotIdx = lastSegment.lastIndexOf(".");
  if (dotIdx === -1) return null;
  const page = lastSegment.slice(0, dotIdx);
  const lang = lastSegment.slice(dotIdx + 1);
  const key = [...segments.slice(0, -1), page].join(".");
  return { key, lang };
}

// ---------------------------------------------------------------------------
// Registry (built automatically from discovered files)
// ---------------------------------------------------------------------------

const DOC_REGISTRY: DocRegistry = {};

for (const [path, content] of Object.entries(_rawDocs)) {
  const result = _pathToKeyAndLang(path);
  if (!result) continue;
  const { key, lang } = result;
  if (!DOC_REGISTRY[key]) DOC_REGISTRY[key] = {} as DocVariants;
  DOC_REGISTRY[key][lang] = content;
}

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
