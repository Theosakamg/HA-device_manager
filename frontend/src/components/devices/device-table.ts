/**
 * Device table view - shows all devices in a sortable, filterable table.
 */
import { LitElement, html, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import sharedStyles from "../../styles/shared.css?lit";
import deviceTableStyles from "./device-table.css?lit";
import { i18n, localized } from "../../i18n";
import { DeviceClient } from "../../api/device-client";
import type { DmDevice } from "../../types/device";
import { buildHttpFromIp, deviceLabel } from "../../utils/computed-fields";
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
  thClass?: string;
}

@localized
@customElement("dm-device-table")
export class DmDeviceTable extends LitElement {
  static styles = [sharedStyles, deviceTableStyles];

  /** Sortable columns definition (getter so labels update on lang change). */
  private get _columns(): DeviceColumn[] {
    return [
      { key: "enabled", label: i18n.t("device_enabled") },
      { key: "state", label: i18n.t("device_state") },
      { key: "mac", label: "MAC" },
      { key: "displayName", label: i18n.t("device_location") },
      { key: "floor.name", label: i18n.t("device_level") },
      { key: "room.name", label: i18n.t("device_room") },
      { key: "refs.functionName", label: i18n.t("device_function") },
      { key: "positionName", label: i18n.t("device_position_name") },
      { key: "refs.firmwareName", label: i18n.t("device_firmware") },
      { key: "refs.modelName", label: i18n.t("device_model") },
      { key: "refs.targetMac", label: i18n.t("device_target") },
      {
        key: "lastDeployStatus",
        label: i18n.t("device_last_deploy_status"),
        thClass: "col-deploy-status",
      },
      {
        key: "lastDeployAt",
        label: i18n.t("device_last_deploy_at"),
        thClass: "col-deploy-date",
      },
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
  @state() private _selectedIds = new Set<number>();
  @state() private _batchMode = false;
  @state() private _batchDeploying = false;
  @state() private _batchResult: "success" | "error" | null = null;

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
          d.room?.name?.toLowerCase().includes(q) ||
          d.room?.slug?.toLowerCase().includes(q) ||
          d.floor?.name?.toLowerCase().includes(q) ||
          d.floor?.slug?.toLowerCase().includes(q) ||
          d.building?.name?.toLowerCase().includes(q) ||
          d.refs?.modelName?.toLowerCase().includes(q) ||
          d.refs?.firmwareName?.toLowerCase().includes(q) ||
          d.refs?.functionName?.toLowerCase().includes(q) ||
          d.extra?.toLowerCase().includes(q) ||
          d.refs?.targetMac?.toLowerCase().includes(q) ||
          d.lastDeployStatus?.toLowerCase().includes(q) ||
          d.lastDeployAt?.toLowerCase().includes(q)
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

  /** Normalised filter value for a device field.
   * Supports dot-path keys: "refs.modelName", "room.name", "floor.slug", etc.
   */
  private _getFilterValue(device: DmDevice, key: string): string {
    if (key === "enabled") return String(device.enabled);
    if (key === "lastDeployStatus") {
      const s = device.lastDeployStatus;
      if (!s) return i18n.t("deploy_status_none");
      return s === "done"
        ? i18n.t("deploy_status_done")
        : i18n.t("deploy_status_fail");
    }
    // Dot-path traversal for nested keys (e.g. "refs.modelName").
    const parts = key.split(".");
    let val: unknown = device;
    for (const part of parts) {
      if (val == null || typeof val !== "object") {
        val = undefined;
        break;
      }
      val = (val as Record<string, unknown>)[part];
    }
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
                ${searchQuery
                  ? i18n.t("col_filter_no_results")
                  : i18n.t("no_items")}
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
              ${vals.map((v) => this._filterValueLabel(colKey, v)).join(", ")}
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
        <button
          class="filter-clear-btn"
          title="${i18n.t("clear_all_filters")}"
          @click=${this._clearAllFilters}
        >
          ✕ ${i18n.t("clear_all_filters")}
        </button>
        <button
          class="filter-copy-btn ${this._linkCopied ? "copied" : ""}"
          title="${i18n.t("filter_share")}"
          @click=${this._copyFilterLink}
        >
          ${this._linkCopied
            ? "✓ " + i18n.t("filter_link_copied")
            : "🔗 " + i18n.t("filter_share")}
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
            class="btn btn-select-mode ${this._batchMode ? "active" : ""}"
            @click=${this._toggleBatchMode}
            title=${this._batchMode
              ? i18n.t("batch_exit_select_mode")
              : i18n.t("batch_select_mode")}
          >
            ☑
            ${this._batchMode
              ? i18n.t("batch_exit_select_mode")
              : i18n.t("batch_select_mode")}
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

      <dm-doc-block
        .doc=${getDoc("devices.overview")}
        storageKey="devices-overview"
      ></dm-doc-block>

      ${this._renderFilterBadges()} ${this._renderBatchToolbar()}
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
                  ${this._batchMode
                    ? html` <th class="checkbox-cell">
                        <input
                          class="row-checkbox"
                          type="checkbox"
                          .checked=${this._allVisibleSelected}
                          .indeterminate=${this._someVisibleSelected &&
                          !this._allVisibleSelected}
                          @change=${this._toggleAllRows}
                        />
                      </th>`
                    : nothing}
                  ${this._columns.map(
                    (col) => html`
                      <th
                        class="sortable ${col.thClass ?? ""} ${this._sort
                          .key === col.key
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
                    <tr
                      class="${device.id != null &&
                      this._selectedIds.has(device.id)
                        ? "row-selected"
                        : ""}"
                    >
                      ${this._batchMode
                        ? html` <td class="checkbox-cell">
                            <input
                              class="row-checkbox"
                              type="checkbox"
                              .checked=${device.id != null &&
                              this._selectedIds.has(device.id)}
                              @change=${() => {
                                if (device.id != null)
                                  this._toggleRowSelect(device.id);
                              }}
                              @click=${(e: Event) => e.stopPropagation()}
                            />
                          </td>`
                        : nothing}
                      <td class="enabled-dot">
                        <span
                          class="status-dot ${device.enabled
                            ? "status-enabled"
                            : "status-disabled"}"
                        ></span>
                      </td>
                      <td class="state-badge">
                        <span class="state-badge-${device.state}">
                          ${device.state === "deployed"
                            ? "🟢 " + i18n.t("state_deployed")
                            : device.state === "parking"
                              ? "🔵 " + i18n.t("state_parking")
                              : device.state === "out_of_order"
                                ? "🔴 " + i18n.t("state_out_of_order")
                                : device.state === "deployed_hot"
                                  ? "🟠 " + i18n.t("state_deployed_hot")
                                  : (device.state ?? "—")}
                        </span>
                      </td>
                      <td class="mac">${device.mac}</td>
                      <td>${deviceLabel(device)}</td>
                      <td>${device.floor?.name ?? "—"}</td>
                      <td>${device.room?.name ?? "—"}</td>
                      <td>${device.refs?.functionName ?? "—"}</td>
                      <td>${device.positionName}</td>
                      <td>${device.refs?.firmwareName ?? "—"}</td>
                      <td>${device.refs?.modelName ?? "—"}</td>
                      <td class="mac">${device.refs?.targetMac ?? "—"}</td>
                      <td class="deploy-status">
                        ${device.lastDeployStatus === "done"
                          ? html`<span class="deploy-badge deploy-badge-done"
                              >✓ ${i18n.t("deploy_status_done")}</span
                            >`
                          : device.lastDeployStatus === "fail"
                            ? html`<span class="deploy-badge deploy-badge-fail"
                                >✗ ${i18n.t("deploy_status_fail")}</span
                              >`
                            : html`<span class="deploy-badge deploy-badge-none"
                                >${i18n.t("deploy_status_none")}</span
                              >`}
                      </td>
                      <td class="deploy-date">
                        ${device.lastDeployAt
                          ? new Date(device.lastDeployAt + "Z").toLocaleString()
                          : "—"}
                      </td>
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

  // ── Batch selection ────────────────────────────────────────────────────────

  private get _allVisibleSelected(): boolean {
    const visible = this._sortedDevices;
    return (
      visible.length > 0 &&
      visible.every((d) => d.id != null && this._selectedIds.has(d.id))
    );
  }

  private get _someVisibleSelected(): boolean {
    return this._sortedDevices.some(
      (d) => d.id != null && this._selectedIds.has(d.id)
    );
  }

  private _toggleRowSelect(id: number) {
    const next = new Set(this._selectedIds);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    this._selectedIds = next;
  }

  private _toggleAllRows() {
    const visible = this._sortedDevices;
    if (this._allVisibleSelected) {
      const next = new Set(this._selectedIds);
      for (const d of visible) {
        if (d.id != null) next.delete(d.id);
      }
      this._selectedIds = next;
    } else {
      const next = new Set(this._selectedIds);
      for (const d of visible) {
        if (d.id != null) next.add(d.id);
      }
      this._selectedIds = next;
    }
  }

  private _toggleBatchMode() {
    this._batchMode = !this._batchMode;
    if (!this._batchMode) {
      this._selectedIds = new Set();
      this._batchResult = null;
    }
  }

  private _renderBatchToolbar() {
    if (!this._batchMode) return nothing;
    return html`
      <div class="batch-toolbar">
        <span class="batch-count">
          <span class="batch-count-badge">${this._selectedIds.size}</span>
          ${i18n.t("batch_selected")}
        </span>
        ${this._batchResult === "success"
          ? html`<span class="batch-result batch-result-ok"
              >✓ ${i18n.t("batch_deploy_triggered")}</span
            >`
          : this._batchResult === "error"
            ? html`<span class="batch-result batch-result-err"
                >✗ ${i18n.t("batch_deploy_error")}</span
              >`
            : nothing}
        <button
          class="btn btn-secondary"
          @click=${() => {
            this._selectedIds = new Set();
          }}
        >
          ${i18n.t("batch_clear_selection")}
        </button>
        <button
          class="btn btn-primary"
          ?disabled=${this._batchDeploying}
          @click=${this._deploySelected}
        >
          🚀 ${this._batchDeploying ? "…" : i18n.t("batch_deploy_selected")}
        </button>
      </div>
    `;
  }

  private async _deploySelected() {
    if (this._selectedIds.size === 0) return;
    this._batchDeploying = true;
    this._batchResult = null;
    try {
      const macs = this._devices
        .filter((d) => d.id != null && this._selectedIds.has(d.id))
        .map((d) => d.mac);
      await this._client.deployBatch(macs);
      this._batchResult = "success";
      setTimeout(async () => {
        await this._load();
        this._batchResult = null;
        this._selectedIds = new Set();
      }, 3000);
    } catch (err) {
      console.error("Batch deploy failed:", err);
      this._batchResult = "error";
      setTimeout(() => {
        this._batchResult = null;
      }, 4000);
    }
    this._batchDeploying = false;
  }
}
