/**
 * Device table view - shows all devices in a sortable, filterable table.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";
import { DeviceClient } from "../../api/device-client";
import { getSettings } from "../../api/settings-client";
import type { DmDevice } from "../../types/device";
import "../shared/confirm-dialog";
import "./deploy-modal";
import "./device-form";
import {
  SortState,
  toggleSort,
  sortIndicator,
  sortItems,
} from "../../utils/sorting";

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
    `,
  ];

  /** Sortable columns definition (getter so labels update on lang change). */
  private get _columns(): DeviceColumn[] {
    return [
      { key: "enabled", label: "" },
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
  @state() private _sort: SortState = { key: null, dir: null };
  @state() private _confirmOpen = false;
  @state() private _pendingDeleteDevice: DmDevice | null = null;

  private _client = new DeviceClient();

  async connectedCallback() {
    super.connectedCallback();
    this._readFilterFromHash();
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

  /** Read an optional ?filter= param from the hash URL. */
  private _readFilterFromHash() {
    const hash = window.location.hash;
    const qIdx = hash.indexOf("?");
    if (qIdx === -1) {
      this._filterFromHash = false;
      return;
    }
    const params = new URLSearchParams(hash.substring(qIdx));
    const filter = params.get("filter");
    if (filter) {
      this._filter = filter;
      this._filterFromHash = true;
    } else {
      this._filterFromHash = false;
    }
  }

  /** Clear the hash filter param and reset search. */
  private _clearHashFilter() {
    this._filter = "";
    this._filterFromHash = false;
    // Remove query param from hash, keep route
    window.location.hash = "#devices";
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
    if (!this._filter) {
      this._filteredDevices = [...this._devices];
      return;
    }
    const q = this._filter.toLowerCase();
    this._filteredDevices = this._devices.filter(
      (d) =>
        d.mac?.toLowerCase().includes(q) ||
        d.ip?.toLowerCase().includes(q) ||
        d.positionName?.toLowerCase().includes(q) ||
        d.roomName?.toLowerCase().includes(q) ||
        d.modelName?.toLowerCase().includes(q) ||
        d.firmwareName?.toLowerCase().includes(q) ||
        d.functionName?.toLowerCase().includes(q)
    );
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
                          : ""}"
                        @click=${() => this._toggleSort(col.key)}
                      >
                        ${col.label}<span class="sort-icon"
                          >${this._sortIcon(col.key)}</span
                        >
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
                              href="${this._buildDeviceUrl(device.ip)}"
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
              @form-save=${this._onFormSave}
              @form-cancel=${() => {
                this._showForm = false;
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
    `;
  }

  private _openCreate() {
    this._editingDevice = null;
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

  /** Build a proper URL from an IP value.
   *
   * Only allows numeric last octets (with ip_prefix) or valid IPv4 addresses.
   * Rejects arbitrary URLs to prevent open redirect / phishing.
   */
  private _buildDeviceUrl(ip: string): string {
    const s = ip.trim();
    // Numeric-only: last octet, prepend ip_prefix
    if (/^\d+$/.test(s) && Number(s) >= 0 && Number(s) <= 255) {
      const { ip_prefix } = getSettings();
      // Validate ip_prefix is a valid partial IP (e.g. "192.168.0")
      if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(ip_prefix)) return "#";
      return `http://${ip_prefix}.${s}/`;
    }
    // Full dotted-quad IPv4
    if (/^\d{1,3}(\.\d{1,3}){3}$/.test(s)) {
      return `http://${s}/`;
    }
    // Reject everything else (URLs, javascript:, etc.)
    return "#";
  }
}
