/**
 * Sorting utility shared by table components.
 *
 * Extracts the common sort logic used in ``device-table`` and ``crud-table``
 * into a single reusable module.
 */

/** Sort direction: ascending, descending, or none. */
export type SortDir = "asc" | "desc" | null;

/** Current sort state. */
export interface SortState {
  key: string | null;
  dir: SortDir;
}

/**
 * Cycle the sort state for a given column key.
 *
 * Cycle: null → asc → desc → null.
 */
export function toggleSort(current: SortState, key: string): SortState {
  if (current.key === key) {
    if (current.dir === "asc") return { key, dir: "desc" };
    return { key: null, dir: null };
  }
  return { key, dir: "asc" };
}

/**
 * Return a sort indicator character for the given column.
 */
export function sortIndicator(current: SortState, key: string): string {
  if (current.key === key) return current.dir === "asc" ? "▲" : "▼";
  return "⇅";
}

/**
 * Sort an array of records by a given key and direction.
 *
 * Handles null, boolean, number and string comparison.
 * Returns a **new** array (does not mutate the original).
 */
export function sortItems<T>(items: T[], state: SortState): T[] {
  if (!state.key || !state.dir) return [...items];
  const key = state.key;
  const dir = state.dir === "asc" ? 1 : -1;

  return [...items].sort((a, b) => {
    const va = (a as Record<string, unknown>)[key];
    const vb = (b as Record<string, unknown>)[key];
    if (va == null && vb == null) return 0;
    if (va == null) return dir;
    if (vb == null) return -dir;
    if (typeof va === "boolean" && typeof vb === "boolean")
      return (Number(va) - Number(vb)) * dir;
    if (typeof va === "number" && typeof vb === "number")
      return (va - vb) * dir;
    return String(va).localeCompare(String(vb)) * dir;
  });
}
