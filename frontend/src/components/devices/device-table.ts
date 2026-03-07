/**
 * Device table view - shows all devices in a sortable, filterable table.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";
import { DeviceClient } from "../../api/device-client";
import type { DmDevice } from "../../types/device";
import { buildHttpFromIp } from "../../utils/computed-fields";
import "../shared/confirm-dialog";
import "./deploy-modal";
import "./device-form";
import {
  SortState,
  toggleSort,
  sortIndicator,
  sortItems,
} from "../../utils/sorting";
import { getDoc } from "../../utils/doc-registry";
import "../shared/doc-block";

/** Column definition for device table sorting. */
interface DeviceColumn {
  key: string;
  label: string;
}

@localized
@customElement("dm-device-table")
export class DmDeviceTable extends LitElement {
  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
      }
      .toolbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 16px;
        flex-wrap: wrap;
        gap: 8px;
      }
      .search-box {
        padding: 8px 12px;
        border: 1px solid var(--dm-border);
        border-radius: 4px;
        font-size: 14px;
        min-width: 200px;
      }
      td.mac {
        font-family: monospace;
        font-size: 12px;
      }
      td.ip {
        font-family: monospace;
        font-size: 12px;
      }
      td.enabled-dot {
        text-align: center;
      }
      .btn-icon-link {
        text-decoration: none;
      }
      th.sortable {
        cursor: pointer;
        user-select: none;
        white-space: nowrap;
      }
      th.sortable:hover {
        background: rgba(0, 0, 0, 0.04);
      }
      .sort-icon {
        display: inline-block;
        margin-left: 4px;
        font-size: 10px;
        opacity: 0.4;
      }
      th.sort-active .sort-icon {
        opacity: 1;
      }
      /* ── Column filter ─────────────────────────────────── */
      th {
        position: relative;
      }
      .th-inner {
        display: flex;
        align-items: center;
        gap: 2px;
      }
      .th-sort-area {
        display: flex;
        align-items: center;
        flex: 1;
        cursor: pointer;
        user-select: none;
      }
      .col-filter-btn {
        flex-shrink: 0;
        background: none;
        border: none;
        padding: 2px 4px;
        border-radius: 3px;
        font-size: 11px;
        cursor: pointer;
        min-width: unset;
        min-height: unset;
        line-height: 1;
        color: var(--dm-text-secondary);
        opacity: 0.45;
        transition:
          opacity 0.15s,
          background 0.15s;
      }
      .col-filter-btn:hover {
        opacity: 1;
        background: rgba(0, 0, 0, 0.08);
      }
      .col-filter-btn.active {
        opacity: 1;
        color: var(--dm-primary);
        background: rgba(3, 169, 244, 0.15);
      }
      th.col-filtered {
        background: rgba(3, 169, 244, 0.06);
      }
      /* Dropdown */
      .col-filter-backdrop {
        position: fixed;
        inset: 0;
        z-index: 999;
      }
      .col-filter-dropdown {
        position: fixed;
        z-index: 1000;
        background: var(--dm-card-bg, #fff);
        border: 1px solid var(--dm-border);
        border-radius: 6px;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.18);
        min-width: 190px;
        max-width: 270px;
        display: flex;
        flex-direction: column;
        overflow: hidden;
      }
      .col-filter-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 8px 10px 6px;
        border-bottom: 1px solid var(--dm-border);
        gap: 6px;
      }
      .col-filter-col-title {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.4px;
        color: var(--dm-text-secondary);
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .col-filter-actions {
        display: flex;
        gap: 4px;
        flex-shrink: 0;
      }
      .col-filter-action-btn {
        background: none;
        border: 1px solid var(--dm-border);
        border-radius: 3px;
        font-size: 11px;
        padding: 2px 7px;
        cursor: pointer;
        color: var(--dm-text-secondary);
        min-width: unset;
        min-height: unset;
        line-height: 1.4;
        transition: background 0.15s;
      }
      .col-filter-action-btn:hover {
        background: rgba(0, 0, 0, 0.06);
        color: var(--dm-text);
      }
      .col-filter-items {
        overflow-y: auto;
        max-height: 230px;
        padding: 4px 0;
      }
      .col-filter-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 5px 12px;
        cursor: pointer;
        font-size: 13px;
        transition: background 0.1s;
      }
      .col-filter-item:hover {
        background: rgba(0, 0, 0, 0.04);
      }
      .col-filter-item input[type="checkbox"] {
        margin: 0;
        accent-color: var(--dm-primary);
        width: 14px;
        height: 14px;
        cursor: pointer;
        flex-shrink: 0;
      }
      .col-filter-item-label {
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .col-filter-no-values {
        padding: 10px 12px;
        font-size: 12px;
        color: var(--dm-text-secondary);
        font-style: italic;
      }
      /* Search inside dropdown */
      .col-filter-search-wrap {
        padding: 6px 8px;
        border-bottom: 1px solid var(--dm-border);
      }
      .col-filter-search {
        width: 100%;
        box-sizing: border-box;
        padding: 5px 8px;
        border: 1px solid var(--dm-border);
        border-radius: 4px;
        font-size: 12px;
        outline: none;
        background: transparent;
        color: var(--dm-text);
        transition: border-color 0.15s;
      }
      .col-filter-search:focus {
        border-color: var(--dm-primary);
        background: rgba(3, 169, 244, 0.04);
      }
      .col-filter-search::placeholder {
        color: var(--dm-text-secondary);
        opacity: 0.7;
      }
      /* Active filter badges bar */
      .filter-active-bar {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 6px;
        margin-bottom: 10px;
        padding: 6px 10px;
        background: rgba(3, 169, 244, 0.05);
        border: 1px solid rgba(3, 169, 244, 0.2);
        border-radius: 6px;
      }
      .filter-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 8px 2px 10px;
        background: rgba(3, 169, 244, 0.12);
        border: 1px solid var(--dm-primary);
        border-radius: 12px;
        font-size: 12px;
        color: var(--dm-text);
        white-space: nowrap;
      }
      .filter-badge strong {
        color: var(--dm-primary);
        font-weight: 600;
      }
      .filter-badge-remove {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 12px;
        padding: 0 0 0 2px;
        min-width: unset;
        min-height: unset;
        color: var(--dm-text-secondary);
        line-height: 1;
      }
      .filter-badge-remove:hover {
        color: var(--dm-error);
      }
      /* Share / copy link button */
      .filter-copy-btn {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 10px;
        background: none;
        border: 1px solid var(--dm-border);
        border-radius: 12px;
        font-size: 12px;
        cursor: pointer;
        color: var(--dm-text-secondary);
        min-width: unset;
        min-height: unset;
        line-height: 1.5;
        transition: background 0.15s, color 0.15s;
      }
      .filter-copy-btn:hover {
        background: rgba(0, 0, 0, 0.06);
        color: var(--dm-text);
      }
      .filter-copy-btn.copied {
        border-color: var(--dm-success);
        color: var(--dm-success);
      }
    `,
  ];

  /** Sortable columns definition (getter so labels update on lang change). */
  private get _columns(): DeviceColumn[] {
    return [
      { key: "enabled", label: i18n.t("device_enabled") },
      { key: "mac", label: "MAC" },
      { key: "floorName", label: i18n.t("device_level") },
      { key: "roomName", label: i18n.t("device_room") },
      { key: "functionName", label: i18n.t("device_function") },
      { key: "positionName", label: i18n.t("device_position_name") },
      { key: "firmwareName", label: i18n.t("device_firmware") },
      { key: "modelName", label: i18n.t("device_model") },
    ];
  }

  @state() private _devices: DmDevice[] = [];
  @state() private _filteredDevices: DmDevice[] = [];
  @state() private _loading = true;
  @state() private _filter = "";
  @state() private _filterFromHash = false;
  @state() private _showForm = false;
  @state() private _showDeploy = false;
  @state() private _editingDevice: DmDevice | null = null;
  @state() private _presetRoomId: number | null = null;
  @state() private _sort: SortState = { key: null, dir: null };
  @state() private _confirmOpen = false;
  @state() private _pendingDeleteDevice: DmDevice | null = null;
  // Column filters
  @state() private _colFilters: Record<string, string[]> = {};
  @state() private _openFilterCol: string | null = null;
  @state() private _filterDropdownPos = { top: 0, left: 0 };
  @state() private _colFilterSearch: Record<string, string> = {};
  @state() private _linkCopied = false;

  private static readonly _STORAGE_KEY = "dm-device-filters";

  private _client = new DeviceClient();

  async connectedCallback() {
    super.connectedCallback();
    const hasHashFilters = this._readFilterFromHash();
    if (!hasHashFilters) {
      this._restoreFiltersFromStorage();
    }
    window.addEventListener("hashchange", this._onHashChange);
    await this._load();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener("hashchange", this._onHashChange);
  }

  private _onHashChange = () => {
    this._readFilterFromHash();
    this._applyFilter();
  };

  /** Read filter params from the hash URL. Returns true if any filter param was found. */
  private _readFilterFromHash(): boolean {
    const hash = window.location.hash;
    const qIdx = hash.indexOf("?");
    if (qIdx === -1) {
      this._filterFromHash = false;
      return false;
    }
    const params = new URLSearchParams(hash.substring(qIdx));
    let hasHashFilters = false;
    const filter = params.get("filter");
    if (filter) {
      this._filter = filter;
      this._filterFromHash = true;
      hasHashFilters = true;
    } else {
      this._filterFromHash = false;
    }
    const cfilters = params.get("cfilters");
    if (cfilters) {
      try {
        const parsed = JSON.parse(cfilters);
        if (parsed && typeof parsed === "object") {
          this._colFilters = parsed as Record<string, string[]>;
          hasHashFilters = true;
        }
      } catch {
        /* ignore malformed */
      }
    }
    const create = params.get("create");
    if (create?.startsWith("room:")) {
      const roomId = parseInt(create.split(":")[1], 10);
      if (!isNaN(roomId)) {
        this._presetRoomId = roomId;
        this._editingDevice = null;
        this._showForm = true;
        // Clean the hash so a page refresh doesn't re-open the form
        window.location.hash = "#devices";
      }
    }
    return hasHashFilters;
  }

  /** Clear the hash filter param and reset search. */
  private _clearHashFilter() {
    this._filter = "";
    this._filterFromHash = false;
    this._applyFilter();
  }

  private async _load() {
    this._loading = true;
    try {
      this._devices = await this._client.getAll();
      this._applyFilter();
    } catch (err) {
      console.error("Failed to load devices:", err);
    }
    this._loading = false;
  }

  private _applyFilter() {
    let result = [...this._devices];
    // Text search
    if (this._filter) {
      const q = this._filter.toLowerCase();
      result = result.filter(
        (d) =>
          d.mac?.toLowerCase().includes(q) ||
          d.ip?.toLowerCase().includes(q) ||
          d.positionName?.toLowerCase().includes(q) ||
          d.positionSlug?.toLowerCase().includes(q) ||
          d.roomName?.toLowerCase().includes(q) ||
          d.roomSlug?.toLowerCase().includes(q) ||
          d.floorName?.toLowerCase().includes(q) ||
          d.floorSlug?.toLowerCase().includes(q) ||
          d.buildingName?.toLowerCase().includes(q) ||
          d.modelName?.toLowerCase().includes(q) ||
          d.firmwareName?.toLowerCase().includes(q) ||
          d.functionName?.toLowerCase().includes(q) ||
          d.extra?.toLowerCase().includes(q)
      );
    }
    // Column filters
    for (const [colKey, selectedVals] of Object.entries(this._colFilters)) {
      if (selectedVals.length === 0) continue;
      result = result.filter((d) =>
        selectedVals.includes(this._getFilterValue(d, colKey))
      );
    }
    this._filteredDevices = result;
    this._syncFiltersToUrl();
    this._syncFiltersToStorage();
  }

  /** Return filtered items sorted by current sort state. */
  private get _sortedDevices(): DmDevice[] {
    return sortItems(this._filteredDevices, this._sort);
  }

  /** Toggle sort on a column. */
  private _toggleSort(key: string) {
    this._sort = toggleSort(this._sort, key);
  }

  /** Sort indicator for a column header. */
  private _sortIcon(key: string): string {
    return sortIndicator(this._sort, key);
  }

  // ── Column filter helpers ──────────────────────────────────────────────────

  /** Sync current filter state to the URL hash (uses replaceState, no hashchange event). */
  private _syncFiltersToUrl() {
    const hash = window.location.hash;
    const route = hash.split("?")[0] || "#devices";
    const params = new URLSearchParams();
    if (this._filter) params.set("filter", this._filter);
    const nonEmpty = Object.fromEntries(
      Object.entries(this._colFilters).filter(([, v]) => v.length > 0)
    );
    if (Object.keys(nonEmpty).length > 0) {
      params.set("cfilters", JSON.stringify(nonEmpty));
    }
    const qs = params.toString();
    const newHash = qs ? `${route}?${qs}` : route;
    history.replaceState(null, "", newHash);
  }

  /** Persist filter state to sessionStorage (removed when all filters are empty). */
  private _syncFiltersToStorage() {
    const nonEmpty = Object.fromEntries(
      Object.entries(this._colFilters).filter(([, v]) => v.length > 0)
    );
    const hasData = this._filter || Object.keys(nonEmpty).length > 0;
    if (hasData) {
      sessionStorage.setItem(
        DmDeviceTable._STORAGE_KEY,
        JSON.stringify({ filter: this._filter, colFilters: nonEmpty })
      );
    } else {
      sessionStorage.removeItem(DmDeviceTable._STORAGE_KEY);
    }
  }

  /** Restore filter state from sessionStorage. Returns true if data was found. */
  private _restoreFiltersFromStorage(): boolean {
    const raw = sessionStorage.getItem(DmDeviceTable._STORAGE_KEY);
    if (!raw) return false;
    try {
      const parsed = JSON.parse(raw) as {
        filter?: string;
        colFilters?: Record<string, string[]>;
      };
      this._filter = parsed.filter ?? "";
      this._colFilters = parsed.colFilters ?? {};
      return true;
    } catch {
      return false;
    }
  }

  /** Copy the current URL (with filters encoded) to the clipboard. */
  private _copyFilterLink() {
    navigator.clipboard.writeText(window.location.href).then(() => {
      this._linkCopied = true;
      setTimeout(() => {
        this._linkCopied = false;
      }, 2000);
    });
  }

  /** Normalised filter value for a device field. */
  private _getFilterValue(device: DmDevice, key: string): string {
    if (key === "enabled") return String(device.enabled);
    const val = (device as unknown as Record<string, unknown>)[key];
    if (val === null || val === undefined || val === "") return "—";
    return String(val);
  }

  /** Sorted unique values for a column (computed over all unfiltered devices). */
  private _uniqueColValues(key: string): string[] {
    const values = new Set<string>();
    for (const d of this._devices) values.add(this._getFilterValue(d, key));
    return Array.from(values).sort((a, b) => {
      if (a === "—") return 1;
      if (b === "—") return -1;
      return a.localeCompare(b);
    });
  }

  /** Human-readable label for a filter value (handles booleans). */
  private _filterValueLabel(key: string, val: string): string {
    if (key === "enabled") {
      if (val === "true") return "✓ " + i18n.t("enabled");
      if (val === "false") return "✗ " + i18n.t("disabled");
    }
    return val;
  }

  /** Whether a column has at least one value selected. */
  private _hasColFilter(key: string): boolean {
    return (this._colFilters[key]?.length ?? 0) > 0;
  }

  /** Whether any column filter is currently active (reserved for future use). */
  // private get _hasAnyColFilter(): boolean {
  //   return Object.values(this._colFilters).some((v) => v.length > 0);
  // }

  /** Toggle a checkbox value in a column filter. */
  private _toggleColFilterValue(
    colKey: string,
    value: string,
    checked: boolean
  ) {
    const current = [...(this._colFilters[colKey] ?? [])];
    if (checked && !current.includes(value)) {
      current.push(value);
    } else if (!checked) {
      const idx = current.indexOf(value);
      if (idx !== -1) current.splice(idx, 1);
    }
    const updated = { ...this._colFilters };
    if (current.length === 0) {
      delete updated[colKey];
    } else {
      updated[colKey] = current;
    }
    this._colFilters = updated;
    this._applyFilter();
  }

  /** Select all or clear a column filter. */
  private _selectAllColFilter(colKey: string, selectAll: boolean) {
    const updated = { ...this._colFilters };
    if (selectAll) {
      updated[colKey] = this._uniqueColValues(colKey);
    } else {
      delete updated[colKey];
    }
    this._colFilters = updated;
    this._applyFilter();
  }

  /** Open (or toggle closed) the dropdown for a column. */
  private _openColFilter(e: Event, colKey: string) {
    e.stopPropagation();
    if (this._openFilterCol === colKey) {
      this._openFilterCol = null;
      return;
    }
    const btn = e.currentTarget as HTMLElement;
    const rect = btn.getBoundingClientRect();
    this._filterDropdownPos = { top: rect.bottom + 4, left: rect.left };
    this._openFilterCol = colKey;
  }

  /** Remove a single column filter (called from badge). */
  private _clearColFilter(colKey: string) {
    const updated = { ...this._colFilters };
    delete updated[colKey];
    this._colFilters = updated;
    this._applyFilter();
  }

  /** Clear all column filters AND text search. */
  private _clearAllFilters() {
    this._colFilters = {};
    this._filter = "";
    this._filterFromHash = false;
    this._openFilterCol = null;
    this._colFilterSearch = {};
    this._linkCopied = false;
    this._applyFilter();
  }

  // ── Render helpers ─────────────────────────────────────────────────────────

  /** Render the floating filter dropdown for a given column. */
  private _renderFilterDropdown(colKey: string) {
    const col = this._columns.find((c) => c.key === colKey);
    const colLabel = col?.label || colKey;
    const searchQuery = (this._colFilterSearch[colKey] ?? "").toLowerCase();
    const allUniqueVals = this._uniqueColValues(colKey);
    const uniqueVals = searchQuery
      ? allUniqueVals.filter((v) =>
          this._filterValueLabel(colKey, v).toLowerCase().includes(searchQuery)
        )
      : allUniqueVals;
    const selectedVals = this._colFilters[colKey] ?? [];
    return html`
      <div
        class="col-filter-backdrop"
        @click=${() => {
          this._openFilterCol = null;
        }}
      ></div>
      <div
        class="col-filter-dropdown"
        style="top:${this._filterDropdownPos.top}px; left:${this
          ._filterDropdownPos.left}px"
      >
        <div class="col-filter-header">
          <span class="col-filter-col-title">${colLabel}</span>
          <div class="col-filter-actions">
            <button
              class="col-filter-action-btn"
              @click=${() => this._selectAllColFilter(colKey, true)}
            >
              ${i18n.t("col_filter_select_all")}
            </button>
            <button
              class="col-filter-action-btn"
              @click=${() => this._selectAllColFilter(colKey, false)}
            >
              ${i18n.t("col_filter_clear_col")}
            </button>
          </div>
        </div>
        <div class="col-filter-search-wrap">
          <input
            type="text"
            class="col-filter-search"
            placeholder="${i18n.t("col_filter_search")}"
            .value=${this._colFilterSearch[colKey] ?? ""}
            @input=${(e: Event) => {
              this._colFilterSearch = {
                ...this._colFilterSearch,
                [colKey]: (e.target as HTMLInputElement).value,
              };
            }}
            @click=${(e: Event) => e.stopPropagation()}
          />
        </div>
        <div class="col-filter-items">
          ${uniqueVals.length === 0
            ? html`<div class="col-filter-no-values">
                ${
                  searchQuery
                    ? i18n.t("col_filter_no_results")
                    : i18n.t("no_items")
                }
              </div>`
            : uniqueVals.map(
                (val) => html`
                  <label class="col-filter-item">
                    <input
                      type="checkbox"
                      .checked=${selectedVals.includes(val)}
                      @change=${(e: Event) =>
                        this._toggleColFilterValue(
                          colKey,
                          val,
                          (e.target as HTMLInputElement).checked
                        )}
                    />
                    <span class="col-filter-item-label"
                      >${this._filterValueLabel(colKey, val)}</span
                    >
                  </label>
                `
              )}
        </div>
      </div>
    `;
  }

  /** Render active column filter badges. */
  private _renderFilterBadges() {
    const active = Object.entries(this._colFilters).filter(
      ([, v]) => v.length > 0
    );
    if (active.length === 0) return nothing;
    return html`
      <div class="filter-active-bar">
        ${active.map(([colKey, vals]) => {
          const col = this._columns.find((c) => c.key === colKey);
          return html`
            <span class="filter-badge">
              <strong>${col?.label || colKey}</strong>:
              ${vals
                .map((v) => this._filterValueLabel(colKey, v))
                .join(", ")}
              <button
                class="filter-badge-remove"
                title="${i18n.t("clear_filter")}"
                @click=${() => this._clearColFilter(colKey)}
              >
                ✕
              </button>
            </span>
          `;
        })}
        ${active.length > 1
          ? html`<button
              class="btn btn-secondary"
              style="padding:3px 10px; font-size:12px;"
              @click=${this._clearAllFilters}
            >
              ✕ ${i18n.t("clear_all_filters")}
            </button>`
          : nothing}
        <button
          class="filter-copy-btn ${this._linkCopied ? "copied" : ""}"
          title="${i18n.t("filter_share")}"
          @click=${this._copyFilterLink}
        >
          ${this._linkCopied ? "✓ " + i18n.t("filter_link_copied") : "🔗 " + i18n.t("filter_share")}
        </button>
      </div>
    `;
  }

  render() {
    return html`
      <div class="toolbar">
        <h2>${i18n.t("devices")} (${this._filteredDevices.length})</h2>
        <div style="display:flex; gap:8px; align-items:center;">
          <input
            type="text"
            class="search-box"
            placeholder="🔍 ${i18n.t("search")}..."
            .value=${this._filter}
            @input=${(e: Event) => {
              this._filter = (e.target as HTMLInputElement).value;
              this._filterFromHash = false;
              this._applyFilter();
            }}
          />
          ${this._filterFromHash
            ? html`<button
                class="btn btn-secondary"
                @click=${this._clearHashFilter}
                title="${i18n.t("clear_filter")}"
              >
                ✕ ${i18n.t("clear_filter")}
              </button>`
            : nothing}
          <button class="btn btn-primary" @click=${this._openCreate}>
            + ${i18n.t("add")}
          </button>
          <button
            class="btn btn-primary"
            @click=${() => {
              this._showDeploy = true;
            }}
          >
            🚀 ${i18n.t("deploy")}
          </button>
        </div>
      </div>

      ${this._renderFilterBadges()}

      <dm-doc-block
        .doc=${getDoc("devices.overview")}
        storageKey="devices-overview"
      ></dm-doc-block>

      ${this._loading
        ? html`<div class="loading">${i18n.t("loading")}</div>`
        : nothing}
      ${!this._loading && this._filteredDevices.length === 0
        ? html`<div class="empty-state">${i18n.t("no_devices")}</div>`
        : nothing}
      ${!this._loading && this._filteredDevices.length > 0
        ? html`
            <table>
              <thead>
                <tr>
                  ${this._columns.map(
                    (col) => html`
                      <th
                        class="sortable ${this._sort.key === col.key
                          ? "sort-active"
                          : ""} ${this._hasColFilter(col.key)
                          ? "col-filtered"
                          : ""}"
                      >
                        <div class="th-inner">
                          <span
                            class="th-sort-area"
                            @click=${() => this._toggleSort(col.key)}
                          >
                            ${col.label}<span class="sort-icon"
                              >${this._sortIcon(col.key)}</span
                            >
                          </span>
                          <button
                            class="col-filter-btn ${this._hasColFilter(col.key)
                              ? "active"
                              : ""}"
                            title="${i18n.t("col_filter_title")}"
                            @click=${(e: Event) =>
                              this._openColFilter(e, col.key)}
                          >
                            ▾
                          </button>
                        </div>
                      </th>
                    `
                  )}
                  <th>${i18n.t("actions")}</th>
                </tr>
              </thead>
              <tbody>
                ${this._sortedDevices.map(
                  (device) => html`
                    <tr>
                      <td class="enabled-dot">
                        <span
                          class="status-dot ${device.enabled
                            ? "status-enabled"
                            : "status-disabled"}"
                        ></span>
                      </td>
                      <td class="mac">${device.mac}</td>
                      <td>${device.floorName ?? "—"}</td>
                      <td>${device.roomName ?? "—"}</td>
                      <td>${device.functionName ?? "—"}</td>
                      <td>${device.positionName}</td>
                      <td>${device.firmwareName ?? "—"}</td>
                      <td>${device.modelName ?? "—"}</td>
                      <td>
                        ${device.ip
                          ? html`<a
                              class="btn-icon btn-icon-link"
                              title="Open"
                              href="${buildHttpFromIp(device.ip) ?? "#"}"
                              target="_blank"
                              rel="noopener noreferrer"
                              >🔗</a
                            >`
                          : nothing}
                        <button
                          class="btn-icon"
                          title="${i18n.t("edit")}"
                          @click=${() => this._openEdit(device)}
                        >
                          ✏️
                        </button>
                        <button
                          class="btn-icon"
                          title="${i18n.t("delete")}"
                          @click=${() => this._requestDelete(device)}
                        >
                          🗑️
                        </button>
                      </td>
                    </tr>
                  `
                )}
              </tbody>
            </table>
          `
        : nothing}
      ${this._showForm
        ? html`
            <dm-device-form
              .device=${this._editingDevice}
              .presetRoomId=${this._presetRoomId}
              @form-save=${this._onFormSave}
              @form-cancel=${() => {
                this._showForm = false;
                this._presetRoomId = null;
              }}
            ></dm-device-form>
          `
        : nothing}
      ${this._showDeploy
        ? html`
            <dm-deploy-modal
              .devices=${this._devices}
              @deploy-close=${() => {
                this._showDeploy = false;
              }}
            ></dm-deploy-modal>
          `
        : nothing}

      <dm-confirm-dialog
        .open=${this._confirmOpen}
        .message=${i18n.t("confirm_delete")}
        @dialog-confirm=${this._onConfirmDelete}
        @dialog-cancel=${this._onCancelDelete}
      ></dm-confirm-dialog>

      ${this._openFilterCol !== null
        ? this._renderFilterDropdown(this._openFilterCol)
        : nothing}
    `;
  }

  private _openCreate() {
    this._editingDevice = null;
    this._presetRoomId = null;
    this._showForm = true;
  }

  private _openEdit(device: DmDevice) {
    this._editingDevice = device;
    this._showForm = true;
  }

  private async _onFormSave(e: CustomEvent) {
    const { isEdit, id, data } = e.detail;
    try {
      if (isEdit) {
        await this._client.update(id, data);
      } else {
        await this._client.create(data);
      }
      this._showForm = false;
      await this._load();
    } catch (err) {
      console.error("Failed to save device:", err);
    }
  }

  private _requestDelete(device: DmDevice) {
    this._pendingDeleteDevice = device;
    this._confirmOpen = true;
  }

  private async _onConfirmDelete() {
    this._confirmOpen = false;
    if (!this._pendingDeleteDevice) return;
    try {
      await this._client.remove(this._pendingDeleteDevice.id!);
      this._pendingDeleteDevice = null;
      await this._load();
    } catch (err) {
      console.error("Failed to delete device:", err);
    }
  }

  private _onCancelDelete() {
    this._confirmOpen = false;
    this._pendingDeleteDevice = null;
  }
}
