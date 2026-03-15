/**
 * System view — tabbed interface for import/export, provisioning config, and maintenance.
 */
import { LitElement, html, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import sharedStyles from "../../styles/shared.css?lit";
import systemStyles from "../../styles/system.css?lit";
import systemViewStyles from "./system-view.css?lit";
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
  { id: "common", icon: "⚙️", labelKey: "system_tab_common" },
  { id: "mqtt", icon: "📡", labelKey: "system_tab_mqtt" },
  { id: "wifi", icon: "📶", labelKey: "system_tab_wifi" },
  { id: "zigbee", icon: "🔵", labelKey: "system_tab_zigbee" },
  { id: "maintenance", icon: "🔧", labelKey: "system_tab_maintenance" },
];

@localized
@customElement("dm-system-view")
export class DmSystemView extends LitElement {
  static styles = [sharedStyles, systemStyles, systemViewStyles];

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

  // ── DB backup state ──
  @state() private _dbExporting = false;
  @state() private _dbExportError: string | null = null;
  @state() private _dbImporting = false;
  @state() private _dbImportResult: {
    success: boolean;
    backup: string;
  } | null = null;
  @state() private _dbImportError: string | null = null;

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
              @click=${() => {
                this._activeTab = t.id;
              }}
            >
              <span class="tab-icon">${t.icon}</span>
              ${i18n.t(t.labelKey)}
            </button>
          `
        )}
      </div>

      <!-- Tab panels -->
      ${this._activeTab === "import-export"
        ? this._renderImportExport()
        : nothing}
      ${this._activeTab === "common" ? this._renderCommon() : nothing}
      ${this._activeTab === "mqtt" ? this._renderMQTT() : nothing}
      ${this._activeTab === "wifi" ? this._renderWifi() : nothing}
      ${this._activeTab === "zigbee" ? this._renderZigbee() : nothing}
      ${this._activeTab === "maintenance" ? this._renderMaintenance() : nothing}
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
          <button
            class="btn-export"
            ?disabled=${this._exporting}
            @click=${() => this._exportData("csv")}
          >
            📄 CSV
          </button>
          <button
            class="btn-export"
            ?disabled=${this._exporting}
            @click=${() => this._exportData("json")}
          >
            📝 JSON
          </button>
          <button
            class="btn-export"
            ?disabled=${this._exporting}
            @click=${() => this._exportData("yaml")}
          >
            📑 YAML
          </button>
        </div>
        ${this._exporting
          ? html`<p class="hint" style="margin-top:12px">
              ${i18n.t("loading")}
            </p>`
          : nothing}
        ${this._exportError
          ? html`<div class="result-panel error" style="margin-top:12px">
              <h4>❌ ${i18n.t("error_loading")}</h4>
              <p>${this._exportError}</p>
            </div>`
          : nothing}
      </div>

      <!-- Import CSV -->
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

      <!-- DB Backup -->
      ${this._renderDBBackup()}
    `;
  }

  // ──────────────────────────────────────────────────────────────────
  // DB Backup card
  // ──────────────────────────────────────────────────────────────────

  private _renderDBBackup() {
    return html`
      <div class="card">
        <div class="card-header">
          <span class="card-icon">🗄️</span>
          <h3>${i18n.t("db_backup_title")}</h3>
        </div>
        <p class="hint">${i18n.t("db_backup_desc")}</p>

        <div class="export-actions">
          <!-- Export button -->
          <button
            class="btn-export"
            ?disabled=${this._dbExporting}
            @click=${this._exportDatabase}
          >
            ${this._dbExporting
              ? i18n.t("db_exporting")
              : i18n.t("db_export_btn")}
          </button>

          <!-- Import button (triggers hidden file input) -->
          <button
            class="btn-export"
            ?disabled=${this._dbImporting}
            @click=${this._openDBFilePicker}
          >
            ${this._dbImporting
              ? i18n.t("db_importing")
              : i18n.t("db_import_btn")}
          </button>

          <input
            id="db-file-input"
            type="file"
            accept=".db,.sqlite,.sqlite3"
            style="display:none"
            @change=${this._onDBFileSelected}
          />
        </div>

        ${this._dbExportError
          ? html`<div class="result-panel error" style="margin-top:12px">
              <p>❌ ${this._dbExportError}</p>
            </div>`
          : nothing}
        ${this._dbImportResult
          ? html`<div class="result-panel success" style="margin-top:12px">
              <p>✅ ${i18n.t("db_import_success")}</p>
              <code>${this._dbImportResult.backup}</code>
            </div>`
          : nothing}
        ${this._dbImportError
          ? html`<div class="result-panel error" style="margin-top:12px">
              <p>❌ ${i18n.t("db_import_error")} ${this._dbImportError}</p>
            </div>`
          : nothing}
      </div>
    `;
  }

  // ──────────────────────────────────────────────────────────────────
  // Tab: Common config
  // ──────────────────────────────────────────────────────────────────

  private _renderCommon() {
    const f = this._settingsForm;
    if (!f)
      return html`<div class="card"><p>${i18n.t("config_loading")}</p></div>`;
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
            <input
              type="text"
              .value=${f.ip_prefix}
              @input=${(e: Event) => this._updateSetting("ip_prefix", e)}
            />
            <div class="hint">${i18n.t("config_ip_prefix_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_dns_suffix")}</label>
            <input
              type="text"
              .value=${f.dns_suffix}
              @input=${(e: Event) => this._updateSetting("dns_suffix", e)}
            />
            <div class="hint">${i18n.t("config_dns_suffix_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_default_home")}</label>
            <input
              type="text"
              .value=${f.default_building_name}
              @input=${(e: Event) =>
                this._updateSetting("default_building_name", e)}
            />
            <div class="hint">${i18n.t("config_default_home_hint")}</div>
          </div>
        </div>

        <p class="section-title">${i18n.t("config_device_section")}</p>
        <div class="settings-grid">
          <div class="settings-field">
            <label>${i18n.t("config_device_pass")}</label>
            <input
              type="password"
              .value=${f.device_pass}
              @input=${(e: Event) => this._updateSetting("device_pass", e)}
            />
            <div class="hint">${i18n.t("config_device_pass_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_ntp_server1")}</label>
            <input
              type="text"
              .value=${f.ntp_server1}
              @input=${(e: Event) => this._updateSetting("ntp_server1", e)}
            />
            <div class="hint">${i18n.t("config_ntp_server1_hint")}</div>
          </div>
        </div>

        <p class="section-title">${i18n.t("config_scan_section")}</p>
        <div class="settings-grid">
          <div class="settings-field settings-field--full">
            <label>${i18n.t("config_scan_ssh_key_upload")}</label>
            <div class="ssh-key-field">
              <input
                type="text"
                readonly
                .value=${f.scan_ssh_key_file || ""}
                placeholder="/config/dm/keys/…"
                class="ssh-key-path"
              />
              <label class="btn btn-secondary label-btn-file">
                🔑
                ${this._sshKeyUploading
                  ? i18n.t("config_scan_ssh_key_uploading")
                  : i18n.t("config_scan_ssh_key_upload")}
                <input
                  type="file"
                  hidden
                  ?disabled=${this._sshKeyUploading}
                  @change=${this._onSshKeyFileChange}
                />
              </label>
            </div>
            <div class="hint">${i18n.t("config_scan_ssh_key_upload_hint")}</div>
            ${this._sshKeyToast
              ? html`<div
                  class="hint"
                  style="margin-top:4px;color:${this._sshKeyToast.ok
                    ? "#2e7d32"
                    : "#c62828"}"
                >
                  ${this._sshKeyToast.ok ? "✅" : "❌"} ${this._sshKeyToast.msg}
                </div>`
              : nothing}
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_scan_ssh_user")}</label>
            <input
              type="text"
              .value=${f.scan_ssh_user}
              @input=${(e: Event) => this._updateSetting("scan_ssh_user", e)}
            />
            <div class="hint">${i18n.t("config_scan_ssh_user_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_scan_ssh_host")}</label>
            <input
              type="text"
              .value=${f.scan_ssh_host}
              @input=${(e: Event) => this._updateSetting("scan_ssh_host", e)}
            />
            <div class="hint">${i18n.t("config_scan_ssh_host_hint")}</div>
          </div>
          <div class="settings-field settings-field--full">
            <label>${i18n.t("config_scan_script_content")}</label>
            <div class="security-warning">
              ⚠️ ${i18n.t("config_scan_script_security_warning")}
            </div>
            <textarea
              .value=${f.scan_script_content || ""}
              @input=${(e: Event) =>
                this._updateSetting("scan_script_content", e)}
            ></textarea>
            <div class="hint">${i18n.t("config_scan_script_content_hint")}</div>
          </div>
        </div>

        <p class="section-title">${i18n.t("config_ha_groups_section")}</p>
        <div class="settings-grid">
          <div class="settings-field">
            <label>${i18n.t("config_ha_groups_empty_groups")}</label>
            <input
              type="checkbox"
              .checked=${f.ha_groups_empty_groups === "true"}
              @change=${(e: Event) => {
                if (!this._settingsForm) return;
                this._settingsForm = {
                  ...this._settingsForm,
                  ha_groups_empty_groups: (e.target as HTMLInputElement).checked
                    ? "true"
                    : "false",
                };
              }}
            />
            <div class="hint">
              ${i18n.t("config_ha_groups_empty_groups_hint")}
            </div>
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
    if (!f)
      return html`<div class="card"><p>${i18n.t("config_loading")}</p></div>`;
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
            <input
              type="text"
              .value=${f.bus_host}
              @input=${(e: Event) => this._updateSetting("bus_host", e)}
            />
            <div class="hint">${i18n.t("config_bus_host_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_bus_port")}</label>
            <input
              type="text"
              inputmode="numeric"
              .value=${f.bus_port}
              @input=${(e: Event) => this._updateSetting("bus_port", e)}
            />
            <div class="hint">${i18n.t("config_bus_port_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_bus_username")}</label>
            <input
              type="text"
              .value=${f.bus_username}
              @input=${(e: Event) => this._updateSetting("bus_username", e)}
            />
            <div class="hint">${i18n.t("config_bus_username_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_bus_password")}</label>
            <input
              type="password"
              .value=${f.bus_password}
              @input=${(e: Event) => this._updateSetting("bus_password", e)}
            />
            <div class="hint">${i18n.t("config_bus_password_hint")}</div>
          </div>
        </div>

        <p class="section-title">${i18n.t("system_mqtt_topics")}</p>
        <div class="settings-grid">
          <div class="settings-field">
            <label>${i18n.t("config_mqtt_prefix")}</label>
            <input
              type="text"
              .value=${f.mqtt_topic_prefix}
              @input=${(e: Event) =>
                this._updateSetting("mqtt_topic_prefix", e)}
            />
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
    if (!f)
      return html`<div class="card"><p>${i18n.t("config_loading")}</p></div>`;
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
            <input
              type="text"
              .value=${f.wifi1_ssid}
              @input=${(e: Event) => this._updateSetting("wifi1_ssid", e)}
            />
            <div class="hint">${i18n.t("config_wifi1_ssid_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_wifi1_password")}</label>
            <input
              type="password"
              .value=${f.wifi1_password}
              @input=${(e: Event) => this._updateSetting("wifi1_password", e)}
            />
            <div class="hint">${i18n.t("config_wifi1_password_hint")}</div>
          </div>
        </div>

        <p class="section-title">${i18n.t("system_wifi_fallback")}</p>
        <div class="settings-grid">
          <div class="settings-field">
            <label>${i18n.t("config_wifi2_ssid")}</label>
            <input
              type="text"
              .value=${f.wifi2_ssid}
              @input=${(e: Event) => this._updateSetting("wifi2_ssid", e)}
            />
            <div class="hint">${i18n.t("config_wifi2_ssid_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_wifi2_password")}</label>
            <input
              type="password"
              .value=${f.wifi2_password}
              @input=${(e: Event) => this._updateSetting("wifi2_password", e)}
            />
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
    if (!f)
      return html`<div class="card"><p>${i18n.t("config_loading")}</p></div>`;
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
            <input
              type="text"
              .value=${f.bridge_host}
              @input=${(e: Event) => this._updateSetting("bridge_host", e)}
            />
            <div class="hint">${i18n.t("config_bridge_host_hint")}</div>
          </div>
          <div class="settings-field">
            <label>${i18n.t("config_bridge_devices_config_path")}</label>
            <input
              type="text"
              .value=${f.bridge_devices_config_path}
              @input=${(e: Event) =>
                this._updateSetting("bridge_devices_config_path", e)}
            />
            <div class="hint">
              ${i18n.t("config_bridge_devices_config_path_hint")}
            </div>
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
        <button
          class="btn-scan"
          ?disabled=${this._scanning}
          @click=${this._executeScan}
        >
          ${this._scanning
            ? i18n.t("maint_scan_running")
            : "🔍 " + i18n.t("maint_scan_network")}
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
                ? html`<table class="scan-stats-table">
                      <tr>
                        <td>${i18n.t("maint_scan_stat_total")}</td>
                        <td>
                          <strong>${this._scanResult.stats.total}</strong>
                        </td>
                      </tr>
                      <tr class="text-success">
                        <td>${i18n.t("maint_scan_stat_mapped")}</td>
                        <td>
                          <strong>${this._scanResult.stats.mapped}</strong>
                        </td>
                      </tr>
                      <tr class="text-warning">
                        <td>${i18n.t("maint_scan_stat_not_found")}</td>
                        <td>
                          <strong>${this._scanResult.stats.not_found}</strong>
                        </td>
                      </tr>
                      <tr
                        style="color:${this._scanResult.stats.errors > 0
                          ? "var(--dm-error)"
                          : "inherit"}"
                      >
                        <td style="padding:2px 8px 2px 0">
                          ${i18n.t("maint_scan_stat_errors")}
                        </td>
                        <td>
                          <strong>${this._scanResult.stats.errors}</strong>
                        </td>
                      </tr>
                    </table>
                    ${this._scanResult.stats.error_details?.length
                      ? html`<details style="margin-top:8px;font-size:12px">
                          <summary
                            style="cursor:pointer;color:var(--error-color,#f44336)"
                          >
                            ${i18n.t("maint_scan_stat_error_details")}
                            (${this._scanResult.stats.error_details.length})
                          </summary>
                          <ul style="margin:4px 0;padding-left:16px">
                            ${this._scanResult.stats.error_details.map(
                              (e) => html`<li>${e}</li>`
                            )}
                          </ul>
                        </details>`
                      : nothing}`
                : html`<p style="margin:0;font-size:13px;font-family:monospace">
                    ${this._scanResult.result}
                  </p>`}
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
                  ([table, count]) =>
                    html`<li>
                      ${table}: ${count} ${i18n.t("maint_rows_deleted")}
                    </li>`
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
          <button
            class="btn-danger"
            ?disabled=${this._clearingIP}
            @click=${this._executeClearIPCache}
          >
            ${this._clearingIP
              ? i18n.t("loading")
              : i18n.t("maint_clear_ip_cache")}
          </button>
        </div>
        ${this._clearIPResult
          ? html`<div class="result-panel" style="margin-top:12px">
              <h4>✅ ${i18n.t("maint_clear_ip_cache_success")}</h4>
              <p style="margin:0;font-family:monospace;font-size:13px">
                ${this._clearIPResult.updated}
                ${i18n.t("maint_clear_ip_updated")}
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
        <button
          class="btn btn-primary"
          ?disabled=${this._settingsSaving}
          @click=${this._saveSettings}
        >
          ${this._settingsSaving ? i18n.t("loading") : i18n.t("save")}
        </button>
        ${this._settingsToast
          ? html`<span
              class="settings-toast ${this._settingsToast.ok
                ? "success"
                : "error"}"
            >
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
      <div
        class="confirm-overlay"
        @click=${() => {
          this._showConfirm = false;
        }}
      >
        <div class="confirm-dialog" @click=${(e: Event) => e.stopPropagation()}>
          <h3>⚠️ ${i18n.t("maint_confirm_title")}</h3>
          <p>${i18n.t("maint_confirm_desc")}</p>
          <div class="phrase-hint">${this._confirmPhrase}</div>
          <input
            type="text"
            placeholder="${i18n.t("maint_confirm_placeholder")}"
            .value=${this._confirmInput}
            @input=${(e: Event) => {
              this._confirmInput = (e.target as HTMLInputElement).value;
            }}
          />
          <div class="actions">
            <button
              class="btn btn-secondary"
              @click=${() => {
                this._showConfirm = false;
              }}
            >
              ${i18n.t("cancel")}
            </button>
            <button
              class="btn-danger"
              ?disabled=${!isMatch || this._cleaning}
              @click=${this._executeCleanDB}
            >
              ${this._cleaning
                ? i18n.t("loading")
                : i18n.t("maint_confirm_execute")}
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
      this._cleanResult = await this._maintenanceClient.cleanDB(
        this._confirmPhrase
      );
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
  // DB Backup handlers
  // ──────────────────────────────────────────────────────────────────

  private async _exportDatabase() {
    this._dbExporting = true;
    this._dbExportError = null;
    try {
      await this._maintenanceClient.exportDatabase();
    } catch (err) {
      this._dbExportError = String(err);
    }
    this._dbExporting = false;
  }

  private _openDBFilePicker() {
    const input = this.shadowRoot?.getElementById(
      "db-file-input"
    ) as HTMLInputElement | null;
    input?.click();
  }

  private async _onDBFileSelected(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    if (!confirm(i18n.t("db_import_confirm"))) {
      input.value = "";
      return;
    }

    this._dbImporting = true;
    this._dbImportResult = null;
    this._dbImportError = null;
    try {
      const result = await this._maintenanceClient.importDatabase(file);
      this._dbImportResult = result;
    } catch (err) {
      this._dbImportError = String(err);
    }
    this._dbImporting = false;
    input.value = "";
  }

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
        this._settingsForm = {
          ...this._settingsForm,
          scan_ssh_key_file: result.path,
        };
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
      setTimeout(() => {
        this._sshKeyToast = null;
      }, 6000);
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
    setTimeout(() => {
      this._settingsToast = null;
    }, 4000);
  }
}
