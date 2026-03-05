/**
 * Minimal YAML-frontmatter parser for in-UI documentation pages.
 *
 * Supported syntax:
 * ```markdown
 * ---
 * description: "Short summary shown in the collapsed header"
 * ---
 *
 * Full markdown body rendered in the collapsible section.
 * ```
 *
 * Only the `description` field is extracted. The rest of the frontmatter
 * block is intentionally ignored (keep it simple).
 */

/** Structured content returned after parsing a doc page. */
export interface DocContent {
  /** Short summary — shown in the collapsed header (supports inline markdown). */
  summary: string;
  /** Full body — rendered in the collapsible section (supports full markdown). */
  body: string;
}

/**
 * Parse a markdown string that may start with a YAML frontmatter block.
 *
 * - If a valid `---` block is found, `summary` is taken from the
 *   `description:` field and `body` is the content after the block.
 * - If no frontmatter is present, `summary` is empty and `body` is the full
 *   raw string (graceful degradation).
 *
 * The `description` value may optionally be wrapped in double quotes, which
 * are stripped automatically.
 */
export function parseFrontmatter(raw: string): DocContent {
  // Match the opening ---, the frontmatter block, the closing ---, and the body.
  const match = raw.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);

  if (!match) {
    return { summary: "", body: raw.trim() };
  }

  const frontmatterBlock = match[1];
  const body = match[2].trim();

  // Extract the description line (single-line value, quoted or unquoted).
  const descMatch = frontmatterBlock.match(/^description:\s*(.+)$/m);
  let summary = descMatch ? descMatch[1].trim() : "";

  // Strip optional surrounding double quotes.
  if (summary.startsWith('"') && summary.endsWith('"')) {
    summary = summary.slice(1, -1);
  }

  return { summary, body };
}
