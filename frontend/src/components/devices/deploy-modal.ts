/**
 * Deploy modal - multi-select firmwares and show device mapping results.
 *
 * Displays all available firmwares as checkboxes, lets the user confirm,
 * then shows a result panel (stats + detail table) following the same
 * visual pattern as the import-view component.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";
import { DeviceFirmwareClient } from "../../api/device-firmware-client";
import type {
  DmDevice,
  DeployResult,
  DeployFirmwareDetail,
} from "../../types/device";
import type { DmDeviceFirmware } from "../../types/device-firmware";

@localized
@customElement("dm-deploy-modal")
export class DmDeployModal extends LitElement {
  static styles = [
    sharedStyles,
    css`
      .modal {
        max-width: 650px;
        width: 90vw;
      }
      .modal-body {
        padding: 16px 24px;
        max-height: 65vh;
        overflow-y: auto;
      }

      /* Firmware selection list */
      .firmware-list {
        max-height: 300px;
        overflow-y: auto;
        margin: 12px 0;
      }
      .firmware-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 8px 12px;
        border-bottom: 1px solid var(--dm-border);
        transition: background 0.15s;
      }
      .firmware-item:hover {
        background: rgba(0, 0, 0, 0.03);
      }
      .firmware-item:last-child {
        border-bottom: none;
      }
      .firmware-item input[type="checkbox"] {
        width: 18px;
        height: 18px;
        cursor: pointer;
        accent-color: var(--dm-primary);
      }
      .firmware-item label {
        flex: 1;
        cursor: pointer;
        font-size: 14px;
      }
      .select-actions {
        display: flex;
        gap: 8px;
        margin-bottom: 8px;
      }
      .select-actions button {
        font-size: 12px;
      }

      /* Detail table */
      .detail-section {
        margin-top: 16px;
      }
      .detail-section h4 {
        margin: 0 0 8px;
      }
      .fw-badge {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 500;
        background: #e0e0e0;
        color: var(--dm-text-secondary);
      }

      .empty-fw {
        text-align: center;
        padding: 24px;
        color: var(--dm-text-secondary);
      }
    `,
  ];

  /** All devices passed from the parent table. */
  @property({ type: Array }) devices: DmDevice[] = [];

  @state() private _firmwares: DmDeviceFirmware[] = [];
  @state() private _selectedIds = new Set<number>();
  @state() private _loading = true;
  @state() private _result: DeployResult | null = null;
  @state() private _showErrors = false;

  private _fwClient = new DeviceFirmwareClient();

  async connectedCallback() {
    super.connectedCallback();
    await this._loadFirmwares();
  }

  private async _loadFirmwares() {
    this._loading = true;
    try {
      this._firmwares = await this._fwClient.getAll();
    } catch (err) {
      console.error("Failed to load firmwares:", err);
    }
    this._loading = false;
  }

  /* ---------- selection helpers ---------- */

  private _toggleFirmware(id: number) {
    const next = new Set(this._selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    this._selectedIds = next;
  }

  private _selectAll() {
    this._selectedIds = new Set(this._firmwares.map((f) => f.id!));
  }

  private _deselectAll() {
    this._selectedIds = new Set();
  }

  /* ---------- deploy logic ---------- */

  private _confirmDeploy() {
    const details: DeployFirmwareDetail[] = [];
    const errors: string[] = [];

    for (const fwId of this._selectedIds) {
      const fw = this._firmwares.find((f) => f.id === fwId);
      if (!fw) {
        errors.push(`Firmware ID ${fwId} not found`);
        continue;
      }
      const matched = this.devices.filter((d) => d.firmwareId === fwId);
      details.push({
        firmwareId: fwId,
        firmwareName: fw.name,
        deviceCount: matched.length,
        devices: matched.map((d) => ({
          mac: d.mac,
          positionName: d.positionName,
        })),
      });
    }

    const totalDevices = details.reduce((sum, d) => sum + d.deviceCount, 0);

    this._result = {
      totalDevices,
      firmwaresSelected: this._selectedIds.size,
      details,
      errors,
    };
  }

  private _reset() {
    this._result = null;
    this._selectedIds = new Set();
    this._showErrors = false;
  }

  private _close() {
    this.dispatchEvent(new CustomEvent("deploy-close"));
  }

  /* ---------- render ---------- */

  render() {
    return html`
      <div class="modal-overlay" @click=${this._close}>
        <div class="modal" @click=${(e: Event) => e.stopPropagation()}>
          <div class="modal-header">
            <h2>
              ${this._result
                ? i18n.t("deploy_result_title")
                : i18n.t("deploy_title")}
            </h2>
            <button class="btn-icon" @click=${this._close}>✕</button>
          </div>

          <div class="modal-body">
            ${this._loading
              ? html`<div class="loading">${i18n.t("loading")}</div>`
              : this._result
                ? this._renderResult()
                : this._renderSelection()}
          </div>
        </div>
      </div>
    `;
  }

  /* ---------- Phase 1: firmware selection ---------- */

  private _renderSelection() {
    if (this._firmwares.length === 0) {
      return html`<div class="empty-fw">${i18n.t("deploy_no_firmwares")}</div>`;
    }

    return html`
      <p>${i18n.t("deploy_select_firmwares")}</p>

      <div class="select-actions">
        <button class="btn btn-secondary" @click=${this._selectAll}>
          ${i18n.t("deploy_select_all")}
        </button>
        <button class="btn btn-secondary" @click=${this._deselectAll}>
          ${i18n.t("deploy_deselect_all")}
        </button>
      </div>

      <div class="firmware-list">
        ${this._firmwares.map(
          (fw) => html`
            <div class="firmware-item">
              <input
                type="checkbox"
                id="fw-${fw.id}"
                .checked=${this._selectedIds.has(fw.id!)}
                @change=${() => this._toggleFirmware(fw.id!)}
              />
              <label for="fw-${fw.id}">${fw.name}</label>
              <span
                class="status-dot ${fw.enabled
                  ? "status-enabled"
                  : "status-disabled"}"
              ></span>
            </div>
          `
        )}
      </div>

      <div class="modal-actions">
        <button class="btn btn-secondary" @click=${this._close}>
          ${i18n.t("cancel")}
        </button>
        <button
          class="btn btn-primary"
          ?disabled=${this._selectedIds.size === 0}
          @click=${this._confirmDeploy}
        >
          🚀 ${i18n.t("deploy_confirm")}
        </button>
      </div>
    `;
  }

  /* ---------- Phase 2: results ---------- */

  private _renderResult() {
    const r = this._result!;

    return html`
      <!-- Stats grid -->
      <div class="stats">
        <div class="stat-box selected">
          <div class="stat-value">${r.firmwaresSelected}</div>
          <div class="stat-label">${i18n.t("deploy_firmware_selected")}</div>
        </div>
        <div class="stat-box devices">
          <div class="stat-value">${r.totalDevices}</div>
          <div class="stat-label">${i18n.t("deploy_total_devices")}</div>
        </div>
        ${r.errors.length > 0
          ? html`
              <div
                class="stat-box errors"
                @click=${() => {
                  this._showErrors = !this._showErrors;
                }}
              >
                <div class="stat-value">${r.errors.length}</div>
                <div class="stat-label">
                  ${i18n.t("import_result_errors")} ▼
                </div>
              </div>
            `
          : nothing}
      </div>

      ${r.totalDevices === 0 && r.errors.length === 0
        ? html`<div class="empty-state">${i18n.t("deploy_no_devices")}</div>`
        : nothing}

      <!-- Error panel -->
      ${r.errors.length > 0
        ? html`
            <div class="error-panel">
              <div
                class="error-panel-header"
                @click=${() => {
                  this._showErrors = !this._showErrors;
                }}
              >
                <span
                  >⚠️ ${i18n.t("import_result_errors")}
                  (${r.errors.length})</span
                >
                <span>${this._showErrors ? "▲" : "▼"}</span>
              </div>
              ${this._showErrors
                ? html`
                    <div class="error-panel-body">
                      <ul class="error-list">
                        ${r.errors.map((err) => html`<li>${err}</li>`)}
                      </ul>
                    </div>
                  `
                : nothing}
            </div>
          `
        : nothing}

      <!-- Detail table per firmware -->
      ${r.details.length > 0
        ? html`
            <div class="detail-section">
              <div class="log-table">
                <table>
                  <thead>
                    <tr>
                      <th>${i18n.t("deploy_firmware")}</th>
                      <th>${i18n.t("deploy_device_count")}</th>
                      <th>${i18n.t("deploy_device_mac")}</th>
                      <th>${i18n.t("deploy_device_position")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${r.details.flatMap((detail) =>
                      detail.devices.length > 0
                        ? detail.devices.map(
                            (dev, idx) => html`
                              <tr>
                                <td>
                                  ${idx === 0
                                    ? html`<span class="fw-badge"
                                        >${detail.firmwareName}</span
                                      >`
                                    : ""}
                                </td>
                                <td>${idx === 0 ? detail.deviceCount : ""}</td>
                                <td
                                  style="font-family:monospace;font-size:12px;"
                                >
                                  ${dev.mac}
                                </td>
                                <td>${dev.positionName}</td>
                              </tr>
                            `
                          )
                        : [
                            html`
                              <tr>
                                <td>
                                  <span class="fw-badge"
                                    >${detail.firmwareName}</span
                                  >
                                </td>
                                <td>0</td>
                                <td
                                  colspan="2"
                                  style="color:var(--dm-text-secondary);font-style:italic;"
                                >
                                  —
                                </td>
                              </tr>
                            `,
                          ]
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          `
        : nothing}

      <!-- Actions -->
      <div class="modal-actions">
        <button class="btn btn-secondary" @click=${this._reset}>
          🔄 ${i18n.t("deploy_new")}
        </button>
        <button class="btn btn-primary" @click=${this._close}>
          ${i18n.t("close")}
        </button>
      </div>
    `;
  }
}
