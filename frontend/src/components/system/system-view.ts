/**
 * System view — tabbed interface for import/export, provisioning config, and maintenance.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";
import { MaintenanceClient } from "../../api/maintenance-client";
import type {
  CleanDBResult,
  ClearIPCacheResult,
  ScanResult,
  ExportFormat,
} from "../../api/maintenance-client";
import { SettingsClient, refreshSettings } from "../../api/settings-client";
import type { AppSettings } from "../../api/settings-client";
import { getDoc } from "../../utils/doc-registry";
import "../import/import-view";
import "../shared/doc-block";

type SystemTab =
  | "import-export"
  | "common"
  | "mqtt"
  | "wifi"
  | "zigbee"
  | "maintenance";

const TABS: { id: SystemTab; icon: string; labelKey: string }[] = [
  { id: "import-export", icon: "📦", labelKey: "system_tab_import_export" },
  { id: "common",        icon: "⚙️", labelKey: "system_tab_common" },
  { id: "mqtt",          icon: "📡", labelKey: "system_tab_mqtt" },
  { id: "wifi",          icon: "📶", labelKey: "system_tab_wifi" },
  { id: "zigbee",        icon: "🔵", labelKey: "system_tab_zigbee" },
  { id: "maintenance",   icon: "🔧", labelKey: "system_tab_maintenance" },
];

@localized
@customElement("dm-system-view")
export class DmSystemView extends LitElement {
  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        max-width: 960px;
        margin: 0 auto;
      }

      /* ── Tab bar ── */
      .tab-bar {
        display: flex;
        gap: 2px;
        background: white;
        border-radius: 10px;
        padding: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,.08);
        margin-bottom: 24px;
        flex-wrap: wrap;
      }
      .tab-btn {
        flex: 1;
        min-width: 100px;
        padding: 10px 14px;
        border: none;
        border-radius: 6px;
        background: transparent;
        cursor: pointer;
        font-size: 13px;
        font-weight: 500;
        color: var(--dm-text-secondary, #666);
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 6px;
        transition: background 0.15s, color 0.15s;
        white-space: nowrap;
      }
      .tab-btn:hover {
        background: rgba(3,169,244,.06);
        color: var(--dm-text, #1a1a1a);
      }
      .tab-btn.active {
        background: var(--dm-primary, #03a9f4);
        color: white;
        font-weight: 600;
      }
      .tab-btn .tab-icon {
        font-size: 16px;
      }

      /* ── Content card ── */
      .card {
        background: white;
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,.08);
      }
      .card-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 20px;
      }
      .card-header h3 {
        margin: 0;
        font-size: 16px;
      }
      .card-icon {
        font-size: 22px;
      }
      .section-title {
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .5px;
        color: var(--dm-text-secondary, #888);
        margin: 24px 0 10px;
        border-bottom: 1px solid var(--dm-border, #e8e8e8);
        padding-bottom: 6px;
      }
      .section-title:first-child {
        margin-top: 0;
      }

      /* ── Settings grid ── */
      .settings-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
      }
      @media (max-width: 600px) {
        .settings-grid { grid-template-columns: 1fr; }
        .tab-btn { font-size: 12px; padding: 8px 8px; }
      }
      .settings-field label {
        display: block;
        font-weight: 600;
        margin-bottom: 4px;
        font-size: 14px;
      }
      .settings-field input {
        width: 100%;
        padding: 8px 12px;
        border: 1px solid #ccc;
        border-radius: 4px;
        font-size: 14px;
        box-sizing: border-box;
      }
      .settings-field input:focus {
        outline: none;
        border-color: var(--dm-primary, #03a9f4);
        box-shadow: 0 0 0 2px rgba(3,169,244,.15);
      }
      .hint {
        font-size: 12px;
        color: #888;
        margin-top: 4px;
      }
      .settings-actions {
        margin-top: 20px;
        display: flex;
        gap: 12px;
        align-items: center;
      }
      .settings-toast {
        font-size: 13px;
        padding: 6px 12px;
        border-radius: 4px;
      }
      .settings-toast.success { background: #e8f5e9; color: #2e7d32; }
      .settings-toast.error   { background: #fce4ec; color: #c62828; }

      /* ── Export ── */
      .export-actions {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        align-items: center;
      }
      .btn-export {
        padding: 10px 20px;
        border: 2px solid var(--dm-primary, #03a9f4);
        border-radius: 6px;
        background: white;
        cursor: pointer;
        font-weight: 600;
        font-size: 14px;
        color: var(--dm-primary, #03a9f4);
        transition: all 0.15s;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .btn-export:hover { background: var(--dm-primary, #03a9f4); color: white; }
      .btn-export:disabled { opacity: 0.5; cursor: not-allowed; }

      /* ── Scan ── */
      .btn-scan {
        padding: 10px 24px;
        border: none;
        border-radius: 6px;
        background: #0288d1;
        color: white;
        cursor: pointer;
        font-weight: 600;
        font-size: 14px;
        transition: background 0.15s;
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .btn-scan:hover { background: #0277bd; }
      .btn-scan:disabled { background: #e0e0e0; color: #999; cursor: not-allowed; }
      .scan-progress {
        margin-top: 16px;
        display: flex;
        align-items: center;
        gap: 12px;
        color: #0288d1;
        font-size: 14px;
        font-weight: 600;
      }
      .scan-spinner {
        width: 20px;
        height: 20px;
        border: 3px solid #bbdefb;
        border-top-color: #0288d1;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
        flex-shrink: 0;
      }
      @keyframes spin { to { transform: rotate(360deg); } }

      /* ── Result panels ── */
      .result-panel {
        margin-top: 16px;
        padding: 16px;
        border-radius: 8px;
        background: #e8f5e9;
        border: 1px solid #a5d6a7;
      }
      .result-panel.error { background: #fce4ec; border-color: #ef9a9a; }
      .result-panel h4 { margin: 0 0 8px 0; }
      .result-list {
        list-style: none; padding: 0; margin: 0; font-size: 13px;
      }
      .result-list li { padding: 4px 0; font-family: monospace; }

      /* ── Danger zone ── */
      .danger-zone {
        border: 2px solid #e57373;
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 0;
      }
      .danger-zone h3 { color: #c62828; margin: 0 0 8px 0; }
      .danger-action {
        display: flex;
        align-items: flex-start;
        gap: 16px;
        padding: 16px;
        background: #fff8f8;
        border-radius: 8px;
        border: 1px solid #ffcdd2;
        margin-top: 12px;
      }
      .danger-action-info { flex: 1; }
      .danger-action-info h4 { margin: 0 0 4px 0; color: #b71c1c; }
      .danger-action-info p  { margin: 0; font-size: 13px; color: #666; }
      .btn-danger {
        padding: 8px 20px;
        border: none;
        border-radius: 4px;
        background: #c62828;
        color: white;
        cursor: pointer;
        font-weight: 600;
        white-space: nowrap;
        transition: background 0.15s;
      }
      .btn-danger:hover { background: #b71c1c; }
      .btn-danger:disabled { background: #e0e0e0; cursor: not-allowed; color: #999; }

      /* ── Confirm overlay ── */
      .confirm-overlay {
        position: fixed;
        inset: 0;
        background: rgba(0,0,0,.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
      }
      .confirm-dialog {
        background: white;
        border-radius: 12px;
        padding: 32px;
        max-width: 440px;
        width: 90%;
        box-shadow: 0 8px 32px rgba(0,0,0,.2);
      }
      .confirm-dialog h3 { color: #c62828; margin: 0 0 12px 0; }
      .confirm-dialog p  { color: #666; font-size: 14px; margin: 0 0 16px 0; }
      .phrase-hint {
        background: #fce4ec;
        padding: 8px 12px;
        border-radius: 4px;
        font-family: monospace;
        font-weight: bold;
        color: #c62828;
        text-align: center;
        margin-bottom: 12px;
        font-size: 16px;
      }
      .confirm-dialog input {
        width: 100%;
        padding: 10px 12px;
        border: 2px solid #e0e0e0;
        border-radius: 4px;
        font-size: 14px;
        box-sizing: border-box;
        margin-bottom: 16px;
        font-family: monospace;
      }
      .confirm-dialog input:focus { outline: none; border-color: #c62828; }
      .confirm-dialog .actions {
        display: flex;
        gap: 12px;
        justify-content: flex-end;
      }
    `,
  ];

  // ── Active tab ──
  @state() private _activeTab: SystemTab = "common";

  // ── Maintenance states ──
  @state() private _showConfirm = false;
  @state() private _confirmInput = "";
  @state() private _cleaning = false;
  @state() private _cleanResult: CleanDBResult | null = null;
  @state() private _cleanError: string | null = null;
  @state() private _scanning = false;
  @state() private _scanResult: ScanResult | null = null;
  @state() private _scanError: string | null = null;
  @state() private _clearingIP = false;
  @state() private _clearIPResult: ClearIPCacheResult | null = null;
  @state() private _clearIPError: string | null = null;

  // ── Export state ──
  @state() private _exporting = false;
  @state() private _exportError: string | null = null;

  // ── Settings state ──
  @state() private _settingsForm: AppSettings | null = null;
  @state() private _settingsSaving = false;
  @state() private _settingsToast: { msg: string; ok: boolean } | null = null;

  // ── SSH key upload state ──
  @state() private _sshKeyUploading = false;
  @state() private _sshKeyToast: { msg: string; ok: boolean } | null = null;

  private _maintenanceClient = new MaintenanceClient();
  private _settingsClient = new SettingsClient();
  private readonly _confirmPhrase = "DELETE ALL DATA";

  connectedCallback(): void {
    super.connectedCallback();
    this._loadSettings();
  }

  // ── Render ──

  render() {
    return html`
      <h2>🖥️ ${i18n.t("nav_system")}</h2>

      <!-- Tab bar -->
      <div class="tab-bar" role="tablist">
        ${TABS.map(
          (t) => html`
            <button
              class="tab-btn ${this._activeTab === t.id ? "active" : ""}"
              role="tab"
              aria-selected="${this._activeTab === t.id}"
              @click=${() => { this._activeTab = t.id; }}
            >
              <span class="tab-icon">${t.icon}</span>
              ${i18n.t(t.labelKey)}
            </button>
          `
        )}
      </div>

      <!-- Tab panels -->
      ${this._activeTab === "import-export" ? this._renderImportExport() : nothing}
      ${this._activeTab === "common"        ? this._renderCommon()       : nothing}
      ${this._activeTab === "mqtt"          ? this._renderMQTT()         : nothing}
      ${this._activeTab === "wifi"          ? this._renderWifi()         : nothing}
      ${this._activeTab === "zigbee"        ? this._renderZigbee()       : nothing}
      ${this._activeTab === "maintenance"   ? this._renderMaintenance()  : nothing}

      ${this._showConfirm ? this._renderConfirmDialog() : nothing}
    `;
  }

  // ──────────────────────────────────────────────────────────────────
  // Tab: Import / Export
  // ──────────────────────────────────────────────────────────────────

  private _renderImportExport() {
    return html`
      <!-- Export -->
      <div class="card">
        <div class="card-header">
          <span class="card-icon">📤</span>
          <h3>${i18n.t("export_title")}</h3>
        </div>
        <dm-doc-block
          .doc=${getDoc("maintenance.export.overview")}
          storageKey="system-export"
        ></dm-doc-block>
        <div class="export-actions">
          <button class="btn-export" ?disabled=${this._exporting} @click=${() => this._exportData("csv")}>
            📄 CSV
          </button>
          <button class="btn-export" ?disabled=${this._exporting} @click=${() => this._exportData("json")}>
            📝 JSON
          </button>
          <button class="btn-export" ?disabled=${this._exporting} @click=${() => this._exportData("yaml")}>
            📑 YAML
          </button>
        </div>
        ${this._exporting ? html`<p class="hint" style="margin-top:12px">${i18n.t("loading")}</p>` : nothing}
        ${this._exportError
          ? html`<div class="result-panel error" style="margin-top:12px">
              <h4>❌ ${i18n.t("error_loading")}</h4>
              <p>${this._exportError}</p>
            </div>`
          : nothing}
      </div>

      <!-- Import -->
      <div class="card">
        <div class="card-header">
          <span class="card-icon">📥</span>
          <h3>${i18n.t("import_csv")}</h3>
        </div>
        <dm-doc-block
          .doc=${getDoc("maintenance.import.overview")}
          storageKey="system-import"
        ></dm-doc-block>
        <dm-import-view></dm-import-view>
      </div>
    `;
  }

  // ──────────────────────────────────────────────────────────────────
  // Tab: Common config
  // ──────────────────────────────────────────────────────────────────

  private _renderCommon() {
    const f = this._settingsForm;
    if (!f) return html`<div class="card"><p>${i18n.t("config_loading")}</p></div>`;
    return html`
      <div class="card">
        <div class="card-header">
          <span class="card-icon">⚙️</span>
          <h3>${i18n.t("system_tab_common")}</h3>
        </div>

        <p class="section-title">${i18n.t("system_common_network")}</p>
        <div class="settings-grid">
          <div class="settings-field">
            <label>${i18n.t("config_ip_prefix")}</label>
            <input type="text" .value=${f.ip_prefix}
              @input=${(e: Event) => this._updateSetting("ip_prefix", e)} />
            <div class="hint">${i18n.t("config_ip_prefix_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_dns_suffix")}</label>
            <input type="text" .value=${f.dns_suffix}
              @input=${(e: Event) => this._updateSetting("dns_suffix", e)} />
            <div class="hint">${i18n.t("config_dns_suffix_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_default_home")}</label>
            <input type="text" .value=${f.default_building_name}
              @input=${(e: Event) => this._updateSetting("default_building_name", e)} />
            <div class="hint">${i18n.t("config_default_home_hint")}</div>
          </div>
        </div>

        <p class="section-title">${i18n.t("config_device_section")}</p>
        <div class="settings-grid">
          <div class="settings-field">
            <label>${i18n.t("config_device_pass")}</label>
            <input type="password" .value=${f.device_pass}
              @input=${(e: Event) => this._updateSetting("device_pass", e)} />
            <div class="hint">${i18n.t("config_device_pass_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_ntp_server1")}</label>
            <input type="text" .value=${f.ntp_server1}
              @input=${(e: Event) => this._updateSetting("ntp_server1", e)} />
            <div class="hint">${i18n.t("config_ntp_server1_hint")}</div>
          </div>
        </div>

        <p class="section-title">${i18n.t("config_scan_section")}</p>
        <div class="settings-grid">
          <div class="settings-field" style="grid-column: span 2">
            <label>${i18n.t("config_scan_ssh_key_upload")}</label>
            <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
              <input type="text" readonly
                .value=${f.scan_ssh_key_file || ""}
                placeholder="/config/dm/keys/…"
                style="flex:1;min-width:200px;background:#f5f5f5;cursor:default"
              />
              <label class="btn btn-secondary" style="cursor:pointer;white-space:nowrap">
                🔑 ${this._sshKeyUploading
                  ? i18n.t("config_scan_ssh_key_uploading")
                  : i18n.t("config_scan_ssh_key_upload")}
                <input type="file" hidden
                  ?disabled=${this._sshKeyUploading}
                  @change=${this._onSshKeyFileChange}
                />
              </label>
            </div>
            <div class="hint">${i18n.t("config_scan_ssh_key_upload_hint")}</div>
            ${this._sshKeyToast
              ? html`<div class="hint" style="margin-top:4px;color:${this._sshKeyToast.ok ? "#2e7d32" : "#c62828"}">
                  ${this._sshKeyToast.ok ? "✅" : "❌"} ${this._sshKeyToast.msg}
                </div>`
              : nothing}
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_scan_ssh_user")}</label>
            <input type="text" .value=${f.scan_ssh_user}
              @input=${(e: Event) => this._updateSetting("scan_ssh_user", e)} />
            <div class="hint">${i18n.t("config_scan_ssh_user_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_scan_ssh_host")}</label>
            <input type="text" .value=${f.scan_ssh_host}
              @input=${(e: Event) => this._updateSetting("scan_ssh_host", e)} />
            <div class="hint">${i18n.t("config_scan_ssh_host_hint")}</div>
          </div>
        </div>

        ${this._renderSettingsActions()}
      </div>
    `;
  }

  // ──────────────────────────────────────────────────────────────────
  // Tab: MQTT
  // ──────────────────────────────────────────────────────────────────

  private _renderMQTT() {
    const f = this._settingsForm;
    if (!f) return html`<div class="card"><p>${i18n.t("config_loading")}</p></div>`;
    return html`
      <div class="card">
        <div class="card-header">
          <span class="card-icon">📡</span>
          <h3>${i18n.t("system_tab_mqtt")}</h3>
        </div>

        <p class="section-title">${i18n.t("config_bus_section")}</p>
        <div class="settings-grid">
          <div class="settings-field">
            <label>${i18n.t("config_bus_host")}</label>
            <input type="text" .value=${f.bus_host}
              @input=${(e: Event) => this._updateSetting("bus_host", e)} />
            <div class="hint">${i18n.t("config_bus_host_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_bus_port")}</label>
            <input type="text" inputmode="numeric" .value=${f.bus_port}
              @input=${(e: Event) => this._updateSetting("bus_port", e)} />
            <div class="hint">${i18n.t("config_bus_port_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_bus_username")}</label>
            <input type="text" .value=${f.bus_username}
              @input=${(e: Event) => this._updateSetting("bus_username", e)} />
            <div class="hint">${i18n.t("config_bus_username_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_bus_password")}</label>
            <input type="password" .value=${f.bus_password}
              @input=${(e: Event) => this._updateSetting("bus_password", e)} />
            <div class="hint">${i18n.t("config_bus_password_hint")}</div>
          </div>
        </div>

        <p class="section-title">${i18n.t("system_mqtt_topics")}</p>
        <div class="settings-grid">
          <div class="settings-field">
            <label>${i18n.t("config_mqtt_prefix")}</label>
            <input type="text" .value=${f.mqtt_topic_prefix}
              @input=${(e: Event) => this._updateSetting("mqtt_topic_prefix", e)} />
            <div class="hint">${i18n.t("config_mqtt_prefix_hint")}</div>
          </div>
        </div>

        ${this._renderSettingsActions()}
      </div>
    `;
  }

  // ──────────────────────────────────────────────────────────────────
  // Tab: WiFi
  // ──────────────────────────────────────────────────────────────────

  private _renderWifi() {
    const f = this._settingsForm;
    if (!f) return html`<div class="card"><p>${i18n.t("config_loading")}</p></div>`;
    return html`
      <div class="card">
        <div class="card-header">
          <span class="card-icon">📶</span>
          <h3>${i18n.t("system_tab_wifi")}</h3>
        </div>

        <p class="section-title">${i18n.t("system_wifi_primary")}</p>
        <div class="settings-grid">
          <div class="settings-field">
            <label>${i18n.t("config_wifi1_ssid")}</label>
            <input type="text" .value=${f.wifi1_ssid}
              @input=${(e: Event) => this._updateSetting("wifi1_ssid", e)} />
            <div class="hint">${i18n.t("config_wifi1_ssid_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_wifi1_password")}</label>
            <input type="password" .value=${f.wifi1_password}
              @input=${(e: Event) => this._updateSetting("wifi1_password", e)} />
            <div class="hint">${i18n.t("config_wifi1_password_hint")}</div>
          </div>
        </div>

        <p class="section-title">${i18n.t("system_wifi_fallback")}</p>
        <div class="settings-grid">
          <div class="settings-field">
            <label>${i18n.t("config_wifi2_ssid")}</label>
            <input type="text" .value=${f.wifi2_ssid}
              @input=${(e: Event) => this._updateSetting("wifi2_ssid", e)} />
            <div class="hint">${i18n.t("config_wifi2_ssid_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_wifi2_password")}</label>
            <input type="password" .value=${f.wifi2_password}
              @input=${(e: Event) => this._updateSetting("wifi2_password", e)} />
            <div class="hint">${i18n.t("config_wifi2_password_hint")}</div>
          </div>
        </div>

        ${this._renderSettingsActions()}
      </div>
    `;
  }

  // ──────────────────────────────────────────────────────────────────
  // Tab: Zigbee
  // ──────────────────────────────────────────────────────────────────

  private _renderZigbee() {
    const f = this._settingsForm;
    if (!f) return html`<div class="card"><p>${i18n.t("config_loading")}</p></div>`;
    return html`
      <div class="card">
        <div class="card-header">
          <span class="card-icon">🔵</span>
          <h3>${i18n.t("system_tab_zigbee")}</h3>
        </div>

        <p class="section-title">${i18n.t("config_bridge_section")}</p>
        <div class="settings-grid">
          <div class="settings-field">
            <label>${i18n.t("config_bridge_host")}</label>
            <input type="text" .value=${f.bridge_host}
              @input=${(e: Event) => this._updateSetting("bridge_host", e)} />
            <div class="hint">${i18n.t("config_bridge_host_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_bridge_devices_config_path")}</label>
            <input type="text" .value=${f.bridge_devices_config_path}
              @input=${(e: Event) => this._updateSetting("bridge_devices_config_path", e)} />
            <div class="hint">${i18n.t("config_bridge_devices_config_path_hint")}</div>
          </div>
        </div>

        ${this._renderSettingsActions()}
      </div>
    `;
  }

  // ──────────────────────────────────────────────────────────────────
  // Tab: Maintenance (scan + danger zone)
  // ──────────────────────────────────────────────────────────────────

  private _renderMaintenance() {
    return html`
      <!-- Network Scan -->
      <div class="card">
        <div class="card-header">
          <span class="card-icon">🔍</span>
          <h3>${i18n.t("maint_scan_network")}</h3>
        </div>
        <dm-doc-block
          .doc=${getDoc("maintenance.scan.overview")}
          storageKey="system-scan"
        ></dm-doc-block>
        <button class="btn-scan" ?disabled=${this._scanning} @click=${this._executeScan}>
          ${this._scanning ? i18n.t("maint_scan_running") : "🔍 " + i18n.t("maint_scan_network")}
        </button>
        ${this._scanning
          ? html`<div class="scan-progress">
              <div class="scan-spinner"></div>
              <span>${i18n.t("maint_scan_running")}</span>
            </div>`
          : nothing}
        ${this._scanResult
          ? html`<div class="result-panel" style="margin-top:16px">
              <h4>✅ ${i18n.t("maint_scan_triggered")}</h4>
              ${this._scanResult.stats
                ? html`<table style="margin-top:8px;border-collapse:collapse;font-size:13px;font-family:monospace;width:100%">
                    <tr><td style="padding:2px 8px 2px 0">${i18n.t("maint_scan_stat_total")}</td><td><strong>${this._scanResult.stats.total}</strong></td></tr>
                    <tr style="color:var(--success-color,#4caf50)"><td style="padding:2px 8px 2px 0">${i18n.t("maint_scan_stat_mapped")}</td><td><strong>${this._scanResult.stats.mapped}</strong></td></tr>
                    <tr style="color:var(--warning-color,#ff9800)"><td style="padding:2px 8px 2px 0">${i18n.t("maint_scan_stat_not_found")}</td><td><strong>${this._scanResult.stats.not_found}</strong></td></tr>
                    <tr style="color:${this._scanResult.stats.errors > 0 ? 'var(--error-color,#f44336)' : 'inherit'}"><td style="padding:2px 8px 2px 0">${i18n.t("maint_scan_stat_errors")}</td><td><strong>${this._scanResult.stats.errors}</strong></td></tr>
                  </table>
                  ${this._scanResult.stats.error_details?.length
                    ? html`<details style="margin-top:8px;font-size:12px">
                        <summary style="cursor:pointer;color:var(--error-color,#f44336)">${i18n.t("maint_scan_stat_error_details")} (${this._scanResult.stats.error_details.length})</summary>
                        <ul style="margin:4px 0;padding-left:16px">${this._scanResult.stats.error_details.map(e => html`<li>${e}</li>`)}</ul>
                      </details>`
                    : nothing}`
                : html`<p style="margin:0;font-size:13px;font-family:monospace">${this._scanResult.result}</p>`}
            </div>`
          : nothing}
        ${this._scanError
          ? html`<div class="result-panel error" style="margin-top:16px">
              <h4>❌ ${i18n.t("error_loading")}</h4>
              <p>${this._scanError}</p>
            </div>`
          : nothing}
      </div>

      <!-- Danger zone -->
      <div class="danger-zone">
        <h3>⚠️ ${i18n.t("maint_danger_zone")}</h3>
        <dm-doc-block
          .doc=${getDoc("maintenance.danger.overview")}
          storageKey="system-danger"
        ></dm-doc-block>

        <!-- Clean DB -->
        <div class="danger-action">
          <div class="danger-action-info">
            <h4>🗑️ ${i18n.t("maint_clean_db")}</h4>
            <p>${i18n.t("maint_clean_db_desc")}</p>
          </div>
          <button
            class="btn-danger"
            @click=${() => {
              this._showConfirm = true;
              this._confirmInput = "";
              this._cleanResult = null;
              this._cleanError = null;
            }}
          >
            ${i18n.t("maint_clean_db")}
          </button>
        </div>
        ${this._cleanResult
          ? html`<div class="result-panel" style="margin-top:12px">
              <h4>✅ ${i18n.t("maint_clean_success")}</h4>
              <ul class="result-list">
                ${Object.entries(this._cleanResult.deleted).map(
                  ([table, count]) => html`<li>${table}: ${count} ${i18n.t("maint_rows_deleted")}</li>`
                )}
              </ul>
            </div>`
          : nothing}
        ${this._cleanError
          ? html`<div class="result-panel error" style="margin-top:12px">
              <h4>❌ ${i18n.t("error_loading")}</h4>
              <p>${this._cleanError}</p>
            </div>`
          : nothing}

        <!-- Clear IP Cache -->
        <div class="danger-action">
          <div class="danger-action-info">
            <h4>🌐 ${i18n.t("maint_clear_ip_cache")}</h4>
            <p>${i18n.t("maint_clear_ip_cache_desc")}</p>
          </div>
          <button class="btn-danger" ?disabled=${this._clearingIP} @click=${this._executeClearIPCache}>
            ${this._clearingIP ? i18n.t("loading") : i18n.t("maint_clear_ip_cache")}
          </button>
        </div>
        ${this._clearIPResult
          ? html`<div class="result-panel" style="margin-top:12px">
              <h4>✅ ${i18n.t("maint_clear_ip_cache_success")}</h4>
              <p style="margin:0;font-family:monospace;font-size:13px">
                ${this._clearIPResult.updated} ${i18n.t("maint_clear_ip_updated")}
              </p>
            </div>`
          : nothing}
        ${this._clearIPError
          ? html`<div class="result-panel error" style="margin-top:12px">
              <h4>❌ ${i18n.t("error_loading")}</h4>
              <p>${this._clearIPError}</p>
            </div>`
          : nothing}
      </div>
    `;
  }

  // ──────────────────────────────────────────────────────────────────
  // Shared settings save bar
  // ──────────────────────────────────────────────────────────────────

  private _renderSettingsActions() {
    return html`
      <div class="settings-actions">
        <button class="btn btn-primary" ?disabled=${this._settingsSaving} @click=${this._saveSettings}>
          ${this._settingsSaving ? i18n.t("loading") : i18n.t("save")}
        </button>
        ${this._settingsToast
          ? html`<span class="settings-toast ${this._settingsToast.ok ? "success" : "error"}">
              ${this._settingsToast.msg}
            </span>`
          : nothing}
      </div>
    `;
  }

  // ──────────────────────────────────────────────────────────────────
  // Confirm dialog
  // ──────────────────────────────────────────────────────────────────

  private _renderConfirmDialog() {
    const isMatch = this._confirmInput === this._confirmPhrase;
    return html`
      <div class="confirm-overlay" @click=${() => { this._showConfirm = false; }}>
        <div class="confirm-dialog" @click=${(e: Event) => e.stopPropagation()}>
          <h3>⚠️ ${i18n.t("maint_confirm_title")}</h3>
          <p>${i18n.t("maint_confirm_desc")}</p>
          <div class="phrase-hint">${this._confirmPhrase}</div>
          <input
            type="text"
            placeholder="${i18n.t("maint_confirm_placeholder")}"
            .value=${this._confirmInput}
            @input=${(e: Event) => { this._confirmInput = (e.target as HTMLInputElement).value; }}
          />
          <div class="actions">
            <button class="btn btn-secondary" @click=${() => { this._showConfirm = false; }}>
              ${i18n.t("cancel")}
            </button>
            <button
              class="btn-danger"
              ?disabled=${!isMatch || this._cleaning}
              @click=${this._executeCleanDB}
            >
              ${this._cleaning ? i18n.t("loading") : i18n.t("maint_confirm_execute")}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  // ──────────────────────────────────────────────────────────────────
  // Actions
  // ──────────────────────────────────────────────────────────────────

  private async _executeScan() {
    this._scanning = true;
    this._scanError = null;
    this._scanResult = null;
    try {
      this._scanResult = await this._maintenanceClient.triggerScan();
    } catch (err) {
      this._scanError = String(err);
    } finally {
      this._scanning = false;
    }
  }

  private async _executeClearIPCache() {
    this._clearingIP = true;
    this._clearIPError = null;
    this._clearIPResult = null;
    try {
      this._clearIPResult = await this._maintenanceClient.clearIPCache();
    } catch (err) {
      this._clearIPError = String(err);
    }
    this._clearingIP = false;
  }

  private async _executeCleanDB() {
    this._cleaning = true;
    this._cleanError = null;
    try {
      this._cleanResult = await this._maintenanceClient.cleanDB(this._confirmPhrase);
    } catch (err) {
      this._cleanError = String(err);
      this._cleanResult = null;
    }
    this._cleaning = false;
    this._showConfirm = false;
  }

  private async _exportData(format: ExportFormat) {
    this._exporting = true;
    this._exportError = null;
    try {
      await this._maintenanceClient.exportData(format);
    } catch (err) {
      this._exportError = String(err);
    }
    this._exporting = false;
  }

  // ──────────────────────────────────────────────────────────────────
  // Settings helpers
  // ──────────────────────────────────────────────────────────────────

  private async _loadSettings() {
    try {
      const s = await this._settingsClient.getAll();
      this._settingsForm = { ...s };
    } catch (err) {
      console.error("Failed to load settings:", err);
    }
  }

  private _updateSetting(key: keyof AppSettings, e: Event) {
    if (!this._settingsForm) return;
    this._settingsForm = {
      ...this._settingsForm,
      [key]: (e.target as HTMLInputElement).value,
    };
  }

  private async _onSshKeyFileChange(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    this._sshKeyUploading = true;
    this._sshKeyToast = null;
    try {
      const result = await this._settingsClient.uploadSshKey(file);
      if (this._settingsForm) {
        this._settingsForm = { ...this._settingsForm, scan_ssh_key_file: result.path };
      }
      this._sshKeyToast = {
        msg: `${i18n.t("config_scan_ssh_key_upload_success")}: ${result.filename}`,
        ok: true,
      };
      await refreshSettings();
    } catch (err) {
      this._sshKeyToast = {
        msg: `${i18n.t("config_scan_ssh_key_upload_error")}: ${err}`,
        ok: false,
      };
    } finally {
      this._sshKeyUploading = false;
      input.value = "";
      setTimeout(() => { this._sshKeyToast = null; }, 6000);
    }
  }

  private async _saveSettings() {
    if (!this._settingsForm) return;
    this._settingsSaving = true;
    this._settingsToast = null;
    try {
      const result = await this._settingsClient.save(this._settingsForm);
      this._settingsForm = { ...result };
      await refreshSettings(result);
      this._settingsToast = { msg: i18n.t("config_saved"), ok: true };
    } catch (err) {
      this._settingsToast = {
        msg: `${i18n.t("config_save_error")}: ${err}`,
        ok: false,
      };
    }
    this._settingsSaving = false;
    setTimeout(() => { this._settingsToast = null; }, 4000);
  }
}
