/**
 * Activity Log view — displays audit trail of config changes and actions.
 * Follows device-table UX conventions: toolbar + col-filter dropdowns + filter badges.
 */
import { LitElement, html, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import sharedStyles from "../../styles/shared.css?lit";
import activityLogStyles from "./activity-log-view.css?lit";
import { i18n, localized } from "../../i18n";
import { ActivityLogClient } from "../../api/activity-log-client";
import type {
  ActivityLogEntry,
  ActivityLogPage,
  ActivityLogFilters,
} from "../../types/activity-log";
import { marked } from "marked";
import DOMPurify from "dompurify";
import {
  SortState,
  toggleSort,
  sortIndicator,
  sortItems,
} from "../../utils/sorting";

function renderMarkdown(md: string): string {
  const raw = marked.parse(md, { async: false }) as string;
  return DOMPurify.sanitize(raw);
}

@localized
@customElement("dm-activity-log-view")
export class DmActivityLogView extends LitElement {
  static styles = [sharedStyles, activityLogStyles];

  // Server-loaded data
  @state() private _page: ActivityLogPage | null = null;
  @state() private _loading = false;
  @state() private _error: string | null = null;

  // Server-side date range (triggers reload)
  @state() private _dateFrom = "";
  @state() private _dateTo = "";
  @state() private _currentPage = 1;

  // Sorting — default: timestamp descending (most recent first)
  @state() private _sort: SortState = { key: "timestamp", dir: "desc" };

  // Client-side filters (applied over loaded items)
  @state() private _textFilter = "";
  @state() private _colFilters: Record<string, string[]> = {};
  @state() private _openFilterCol: string | null = null;
  @state() private _filterDropdownPos = { top: 0, left: 0 };
  @state() private _colFilterSearch: Record<string, string> = {};

  // Expansion
  @state() private _expandedId: number | null = null;

  // Export / purge
  @state() private _exporting = false;
  @state() private _purging = false;
  @state() private _purgedays = 90;

  private _client = new ActivityLogClient();

  connectedCallback() {
    super.connectedCallback();
    this._load();
  }

  // ── Data loading ──────────────────────────────────────────────────────────

  private async _load() {
    this._loading = true;
    this._error = null;
    try {
      const filters: ActivityLogFilters = {
        dateFrom: this._dateFrom || undefined,
        dateTo: this._dateTo || undefined,
        page: this._currentPage,
        pageSize: 100,
      };
      this._page = await this._client.list(filters);
    } catch (err) {
      this._error = String(err);
    } finally {
      this._loading = false;
    }
  }

  // ── Client-side filtering ─────────────────────────────────────────────────

  private _getItemValue(entry: ActivityLogEntry, key: string): string {
    switch (key) {
      case "eventType":
        return entry.eventType ?? "—";
      case "severity":
        return entry.severity ?? "—";
      case "entityType":
        return entry.entityType || "—";
      case "user":
        return entry.user || "—";
      default:
        return "—";
    }
  }

  private _uniqueColValues(key: string): string[] {
    if (!this._page) return [];
    const seen = new Set<string>();
    for (const item of this._page.items)
      seen.add(this._getItemValue(item, key));
    return Array.from(seen).sort((a, b) => {
      if (a === "—") return 1;
      if (b === "—") return -1;
      return a.localeCompare(b);
    });
  }

  private get _filteredItems(): ActivityLogEntry[] {
    if (!this._page) return [];
    let items = [...this._page.items];
    if (this._textFilter) {
      const q = this._textFilter.toLowerCase();
      items = items.filter(
        (e) =>
          e.message?.toLowerCase().includes(q) ||
          e.user?.toLowerCase().includes(q) ||
          e.entityType?.toLowerCase().includes(q) ||
          e.eventType?.toLowerCase().includes(q) ||
          (e.entityId != null && String(e.entityId).includes(q))
      );
    }
    for (const [col, vals] of Object.entries(this._colFilters)) {
      if (vals.length === 0) continue;
      items = items.filter((e) => vals.includes(this._getItemValue(e, col)));
    }
    return items;
  }

  private get _sortedItems(): ActivityLogEntry[] {
    return sortItems(this._filteredItems, this._sort);
  }

  private _toggleSort(key: string) {
    this._sort = toggleSort(this._sort, key);
  }

  private _sortIcon(key: string): string {
    return sortIndicator(this._sort, key);
  }

  private get _hasActiveFilters(): boolean {
    return (
      !!this._textFilter ||
      !!this._dateFrom ||
      !!this._dateTo ||
      Object.values(this._colFilters).some((v) => v.length > 0)
    );
  }

  // ── Col filter interactions (identical to device-table) ───────────────────

  private _hasColFilter(key: string): boolean {
    return (this._colFilters[key]?.length ?? 0) > 0;
  }

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

  private _toggleColFilterValue(
    colKey: string,
    value: string,
    checked: boolean
  ) {
    const current = [...(this._colFilters[colKey] ?? [])];
    if (checked && !current.includes(value)) current.push(value);
    else if (!checked) {
      const idx = current.indexOf(value);
      if (idx !== -1) current.splice(idx, 1);
    }
    const updated = { ...this._colFilters };
    if (current.length === 0) delete updated[colKey];
    else updated[colKey] = current;
    this._colFilters = updated;
  }

  private _selectAllColFilter(colKey: string, selectAll: boolean) {
    const updated = { ...this._colFilters };
    if (selectAll) updated[colKey] = this._uniqueColValues(colKey);
    else delete updated[colKey];
    this._colFilters = updated;
  }

  private _clearColFilter(colKey: string) {
    const updated = { ...this._colFilters };
    delete updated[colKey];
    this._colFilters = updated;
  }

  private _clearAllFilters() {
    this._colFilters = {};
    this._textFilter = "";
    this._dateFrom = "";
    this._dateTo = "";
    this._openFilterCol = null;
    this._colFilterSearch = {};
    this._currentPage = 1;
    this._load();
  }

  // ── Export / Purge ────────────────────────────────────────────────────────

  private async _exportData(format: "csv" | "json") {
    this._exporting = true;
    try {
      await this._client.exportData(format);
    } catch (err) {
      window.dispatchEvent(
        new CustomEvent("show-toast", {
          detail: { message: String(err), type: "error" },
        })
      );
    } finally {
      this._exporting = false;
    }
  }

  private async _purge() {
    if (!this._purgedays || this._purgedays < 1) return;
    this._purging = true;
    try {
      const result = await this._client.purge(this._purgedays);
      window.dispatchEvent(
        new CustomEvent("show-toast", {
          detail: {
            message: `${i18n.t("activity_log_purge_success")}: ${result.deleted}`,
            type: "success",
          },
        })
      );
      this._load();
    } catch (err) {
      window.dispatchEvent(
        new CustomEvent("show-toast", {
          detail: { message: String(err), type: "error" },
        })
      );
    } finally {
      this._purging = false;
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────

  render() {
    const items = this._sortedItems;
    const total = this._page?.total ?? 0;

    return html`
      <!-- Toolbar -->
      <div class="toolbar">
        <h2>📋 ${i18n.t("nav_activity_log")} (${total})</h2>
        <div style="display:flex; gap:8px; align-items:center;">
          <input
            type="text"
            class="search-box"
            placeholder="🔍 ${i18n.t("search")}..."
            .value=${this._textFilter}
            @input=${(e: Event) => {
              this._textFilter = (e.target as HTMLInputElement).value;
            }}
          />
          <button
            class="btn btn-secondary"
            ?disabled=${this._exporting}
            @click=${() => this._exportData("csv")}
          >
            ⬇ CSV
          </button>
          <button
            class="btn btn-secondary"
            ?disabled=${this._exporting}
            @click=${() => this._exportData("json")}
          >
            ⬇ JSON
          </button>
        </div>
      </div>

      <!-- Date range bar -->
      <div class="date-range-bar">
        <label>${i18n.t("activity_log_date_from")}</label>
        <input
          type="datetime-local"
          .value=${this._dateFrom}
          @change=${(e: Event) => {
            const v = (e.target as HTMLInputElement).value;
            // Normalise local datetime-local to UTC ISO string for consistent backend comparison
            this._dateFrom = v ? new Date(v).toISOString() : "";
          }}
        />
        <span class="date-range-sep">→</span>
        <label>${i18n.t("activity_log_date_to")}</label>
        <input
          type="datetime-local"
          .value=${this._dateTo}
          @change=${(e: Event) => {
            const v = (e.target as HTMLInputElement).value;
            // Add :59 seconds so the selected minute is fully included
            this._dateTo = v ? new Date(v + ":59").toISOString() : "";
          }}
        />
        <button
          class="date-apply-btn"
          @click=${() => {
            this._currentPage = 1;
            this._load();
          }}
        >
          🔍 ${i18n.t("activity_log_apply_filters")}
        </button>
        ${this._hasActiveFilters
          ? html`
              <button class="filter-clear-btn" @click=${this._clearAllFilters}>
                ✕ ${i18n.t("activity_log_reset_filters")}
              </button>
            `
          : nothing}
      </div>

      <!-- Active filter badges -->
      ${this._renderFilterBadges()}

      <!-- Loading -->
      ${this._loading
        ? html`<div class="loading">${i18n.t("loading")}</div>`
        : nothing}

      <!-- Error -->
      ${this._error
        ? html`<div class="empty-state">⚠️ ${this._error}</div>`
        : nothing}

      <!-- Table -->
      ${!this._loading && !this._error ? this._renderTable(items) : nothing}

      <!-- Column filter dropdowns (rendered at document level via fixed position) -->
      ${this._openFilterCol
        ? this._renderFilterDropdown(this._openFilterCol)
        : nothing}

      <!-- Purge panel -->
      ${this._renderPurgePanel()}
    `;
  }

  private _colLabel(key: string): string {
    const labels: Record<string, string> = {
      eventType: i18n.t("activity_log_col_type"),
      severity: i18n.t("activity_log_col_severity"),
      entityType: i18n.t("activity_log_col_entity"),
      user: i18n.t("activity_log_col_user"),
    };
    return labels[key] ?? key;
  }

  private _renderFilterBadges() {
    const active = Object.entries(this._colFilters).filter(
      ([, v]) => v.length > 0
    );
    if (active.length === 0) return nothing;
    return html`
      <div class="filter-active-bar">
        ${active.map(
          ([colKey, vals]) => html`
            <span class="filter-badge">
              <strong>${this._colLabel(colKey)}</strong>: ${vals.join(", ")}
              <button
                class="filter-badge-remove"
                title="${i18n.t("clear_filter")}"
                @click=${() => this._clearColFilter(colKey)}
              >
                ✕
              </button>
            </span>
          `
        )}
        <button class="filter-clear-btn" @click=${this._clearAllFilters}>
          ✕ ${i18n.t("clear_all_filters")}
        </button>
      </div>
    `;
  }

  private _renderTable(items: ActivityLogEntry[]) {
    if (items.length === 0) {
      return html`<div class="empty-state">
        ${i18n.t("activity_log_empty")}
      </div>`;
    }
    return html`
      <table>
        <thead>
          <tr>
            <th
              class="sortable ${this._sort.key === "timestamp"
                ? "sort-active"
                : ""}"
            >
              <div class="th-inner">
                <span
                  class="th-sort-area"
                  @click=${() => this._toggleSort("timestamp")}
                >
                  ${i18n.t("activity_log_col_timestamp")}<span class="sort-icon"
                    >${this._sortIcon("timestamp")}</span
                  >
                </span>
              </div>
            </th>
            <th
              class="sortable ${this._sort.key === "user"
                ? "sort-active"
                : ""} ${this._hasColFilter("user") ? "col-filtered" : ""}"
            >
              <div class="th-inner">
                <span
                  class="th-sort-area"
                  @click=${() => this._toggleSort("user")}
                >
                  ${i18n.t("activity_log_col_user")}<span class="sort-icon"
                    >${this._sortIcon("user")}</span
                  >
                </span>
                <button
                  class="col-filter-btn ${this._hasColFilter("user")
                    ? "active"
                    : ""}"
                  title="${i18n.t("col_filter_title")}"
                  @click=${(e: Event) => this._openColFilter(e, "user")}
                >
                  ▾
                </button>
              </div>
            </th>
            <th
              class="sortable ${this._sort.key === "eventType"
                ? "sort-active"
                : ""} ${this._hasColFilter("eventType") ? "col-filtered" : ""}"
            >
              <div class="th-inner">
                <span
                  class="th-sort-area"
                  @click=${() => this._toggleSort("eventType")}
                >
                  ${i18n.t("activity_log_col_type")}<span class="sort-icon"
                    >${this._sortIcon("eventType")}</span
                  >
                </span>
                <button
                  class="col-filter-btn ${this._hasColFilter("eventType")
                    ? "active"
                    : ""}"
                  title="${i18n.t("col_filter_title")}"
                  @click=${(e: Event) => this._openColFilter(e, "eventType")}
                >
                  ▾
                </button>
              </div>
            </th>
            <th
              class="sortable ${this._sort.key === "entityType"
                ? "sort-active"
                : ""} ${this._hasColFilter("entityType") ? "col-filtered" : ""}"
            >
              <div class="th-inner">
                <span
                  class="th-sort-area"
                  @click=${() => this._toggleSort("entityType")}
                >
                  ${i18n.t("activity_log_col_entity")}<span class="sort-icon"
                    >${this._sortIcon("entityType")}</span
                  >
                </span>
                <button
                  class="col-filter-btn ${this._hasColFilter("entityType")
                    ? "active"
                    : ""}"
                  title="${i18n.t("col_filter_title")}"
                  @click=${(e: Event) => this._openColFilter(e, "entityType")}
                >
                  ▾
                </button>
              </div>
            </th>
            <th
              class="sortable ${this._sort.key === "severity"
                ? "sort-active"
                : ""} ${this._hasColFilter("severity") ? "col-filtered" : ""}"
            >
              <div class="th-inner">
                <span
                  class="th-sort-area"
                  @click=${() => this._toggleSort("severity")}
                >
                  ${i18n.t("activity_log_col_severity")}<span class="sort-icon"
                    >${this._sortIcon("severity")}</span
                  >
                </span>
                <button
                  class="col-filter-btn ${this._hasColFilter("severity")
                    ? "active"
                    : ""}"
                  title="${i18n.t("col_filter_title")}"
                  @click=${(e: Event) => this._openColFilter(e, "severity")}
                >
                  ▾
                </button>
              </div>
            </th>
            <th>${i18n.t("activity_log_col_message")}</th>
          </tr>
        </thead>
        <tbody>
          ${items.map((entry) => this._renderRow(entry))}
        </tbody>
      </table>
      ${this._renderPagination()}
    `;
  }

  private _renderRow(entry: ActivityLogEntry) {
    const id = entry.id ?? 0;
    const expanded = this._expandedId === id;

    return html`
      <tr
        class="row-expandable"
        @click=${() => {
          this._expandedId = expanded ? null : id;
        }}
      >
        <td class="col-timestamp">${this._formatTs(entry.timestamp)}</td>
        <td class="col-user">${entry.user}</td>
        <td>
          <span class="event-badge event-badge--${entry.eventType}">
            ${entry.eventType === "config_change"
              ? i18n.t("activity_log_config_change")
              : i18n.t("activity_log_action")}
          </span>
        </td>
        <td class="col-entity">${entry.entityType}</td>
        <td>
          <span class="severity-badge severity-badge--${entry.severity}">
            ${entry.severity}
          </span>
        </td>
        <td class="col-message">
          ${expanded
            ? html`
                <div
                  class="detail-markdown"
                  @click=${(e: Event) => e.stopPropagation()}
                >
                  ${unsafeHTML(renderMarkdown(entry.message))}
                </div>
                ${entry.result
                  ? html`
                      <div class="detail-result-label">
                        ${i18n.t("activity_log_result")}
                      </div>
                      <div
                        class="detail-markdown"
                        @click=${(e: Event) => e.stopPropagation()}
                      >
                        ${unsafeHTML(
                          renderMarkdown("```\n" + entry.result + "\n```")
                        )}
                      </div>
                    `
                  : nothing}
              `
            : html`<div class="message-preview">${entry.message}</div>`}
        </td>
      </tr>
    `;
  }

  private _renderFilterDropdown(colKey: string) {
    const searchQuery = (this._colFilterSearch[colKey] ?? "").toLowerCase();
    const allVals = this._uniqueColValues(colKey);
    const uniqueVals = searchQuery
      ? allVals.filter((v) => v.toLowerCase().includes(searchQuery))
      : allVals;
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
          <span class="col-filter-col-title">${this._colLabel(colKey)}</span>
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
        <div class="col-filter-items">
          ${uniqueVals.length === 0
            ? html`<div
                style="padding:10px 12px; font-size:12px; color:var(--dm-text-secondary)"
              >
                ${i18n.t("no_items")}
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
                    <span class="col-filter-item-label">${val}</span>
                  </label>
                `
              )}
        </div>
      </div>
    `;
  }

  private _renderPagination() {
    const page = this._page;
    if (!page || page.pages <= 1) return nothing;
    return html`
      <div class="pagination">
        <span class="pagination-info">
          ${i18n.t("activity_log_total")}: ${page.total}
        </span>
        <button
          ?disabled=${page.page <= 1}
          @click=${() => {
            this._currentPage = page.page - 1;
            this._load();
          }}
        >
          ← ${i18n.t("previous")}
        </button>
        <span class="page-indicator">${page.page} / ${page.pages}</span>
        <button
          ?disabled=${page.page >= page.pages}
          @click=${() => {
            this._currentPage = page.page + 1;
            this._load();
          }}
        >
          ${i18n.t("next")} →
        </button>
      </div>
    `;
  }

  private _renderPurgePanel() {
    return html`
      <div class="card" style="margin-top:16px">
        <div class="card-header">
          <h3>🗑️ ${i18n.t("activity_log_purge_title")}</h3>
        </div>
        <div class="purge-inline">
          <label>${i18n.t("activity_log_purge_label")}</label>
          <input
            type="number"
            min="1"
            max="3650"
            .value=${this._purgedays > 0 ? String(this._purgedays) : ""}
            @input=${(e: Event) => {
              const v = parseInt((e.target as HTMLInputElement).value, 10);
              this._purgedays = isNaN(v) ? 0 : v;
            }}
          />
          <button
            class="btn btn-danger"
            ?disabled=${this._purging}
            @click=${this._purge}
          >
            🗑️ ${i18n.t("activity_log_purge_btn")}
          </button>
        </div>
      </div>
    `;
  }

  private _formatTs(ts: string): string {
    if (!ts) return "—";
    try {
      return new Date(ts).toLocaleString();
    } catch {
      return ts;
    }
  }
}
