/**
 * Maintenance view - import, settings and database operations.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";
import { MaintenanceClient } from "../../api/maintenance-client";
import type { CleanDBResult, ExportFormat } from "../../api/maintenance-client";
import { SettingsClient, refreshSettings } from "../../api/settings-client";
import type { AppSettings } from "../../api/settings-client";
import "../import/import-view";

@localized
@customElement("dm-maintenance-view")
export class DmMaintenanceView extends LitElement {
  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        max-width: 900px;
        margin: 0 auto;
      }
      .section {
        background: white;
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
      }
      .section-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
      }
      .section-header h3 {
        margin: 0;
      }
      .section-icon {
        font-size: 24px;
      }
      .danger-zone {
        border: 2px solid #e57373;
        border-radius: 8px;
        padding: 24px;
        margin-bottom: 24px;
      }
      .danger-zone h3 {
        color: #c62828;
        margin: 0 0 8px 0;
      }
      .danger-zone p {
        color: #666;
        margin: 0 0 16px 0;
        font-size: 14px;
      }
      .danger-action {
        display: flex;
        align-items: flex-start;
        gap: 16px;
        padding: 16px;
        background: #fff8f8;
        border-radius: 8px;
        border: 1px solid #ffcdd2;
      }
      .danger-action-info {
        flex: 1;
      }
      .danger-action-info h4 {
        margin: 0 0 4px 0;
        color: #b71c1c;
      }
      .danger-action-info p {
        margin: 0;
        font-size: 13px;
        color: #666;
      }
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
      .btn-danger:hover {
        background: #b71c1c;
      }
      .btn-danger:disabled {
        background: #e0e0e0;
        cursor: not-allowed;
        color: #999;
      }
      .confirm-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
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
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
      }
      .confirm-dialog h3 {
        color: #c62828;
        margin: 0 0 12px 0;
      }
      .confirm-dialog p {
        color: #666;
        font-size: 14px;
        margin: 0 0 16px 0;
      }
      .confirm-dialog .phrase-hint {
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
      .confirm-dialog input:focus {
        outline: none;
        border-color: #c62828;
      }
      .confirm-dialog .actions {
        display: flex;
        gap: 12px;
        justify-content: flex-end;
      }
      .result-panel {
        margin-top: 16px;
        padding: 16px;
        border-radius: 8px;
        background: #e8f5e9;
        border: 1px solid #a5d6a7;
      }
      .result-panel.error {
        background: #fce4ec;
        border-color: #ef9a9a;
      }
      .result-panel h4 {
        margin: 0 0 8px 0;
      }
      .result-list {
        list-style: none;
        padding: 0;
        margin: 0;
        font-size: 13px;
      }
      .result-list li {
        padding: 4px 0;
        font-family: monospace;
      }
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
      .btn-export:hover {
        background: var(--dm-primary, #03a9f4);
        color: white;
      }
      .btn-export:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
      .export-info {
        font-size: 13px;
        color: #666;
        margin-top: 8px;
      }
      /* Settings form */
      .settings-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
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
        box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.15);
      }
      .settings-field .hint {
        font-size: 12px;
        color: #888;
        margin-top: 4px;
      }
      .settings-actions {
        margin-top: 16px;
        display: flex;
        gap: 12px;
        align-items: center;
      }
      .settings-toast {
        font-size: 13px;
        padding: 6px 12px;
        border-radius: 4px;
      }
      .settings-toast.success {
        background: #e8f5e9;
        color: #2e7d32;
      }
      .settings-toast.error {
        background: #fce4ec;
        color: #c62828;
      }
    `,
  ];

  @state() private _showConfirm = false;
  @state() private _confirmInput = "";
  @state() private _cleaning = false;
  @state() private _cleanResult: CleanDBResult | null = null;
  @state() private _cleanError: string | null = null;
  @state() private _exporting = false;
  @state() private _exportError: string | null = null;

  // Settings state
  @state() private _settingsForm: AppSettings | null = null;
  @state() private _settingsSaving = false;
  @state() private _settingsToast: { msg: string; ok: boolean } | null = null;

  private _maintenanceClient = new MaintenanceClient();
  private _settingsClient = new SettingsClient();
  private readonly _confirmPhrase = "DELETE ALL DATA";

  connectedCallback(): void {
    super.connectedCallback();
    this._loadSettings();
  }

  render() {
    return html`
      <h2>🔧 ${i18n.t("nav_maintenance")}</h2>

      <!-- Settings Section -->
      <div class="section">
        <div class="section-header">
          <span class="section-icon">⚙️</span>
          <h3>${i18n.t("config_title")}</h3>
        </div>
        <p style="color:#666; font-size:14px; margin:0 0 16px 0;">
          ${i18n.t("config_desc")}
        </p>
        ${this._settingsForm
          ? this._renderSettingsForm()
          : html`<p>${i18n.t("config_loading")}</p>`}
      </div>

      <!-- Export Section -->
      <div class="section">
        <div class="section-header">
          <span class="section-icon">📤</span>
          <h3>${i18n.t("export_title")}</h3>
        </div>
        <p style="color:#666; font-size:14px; margin:0 0 16px 0;">
          ${i18n.t("export_desc")}
        </p>
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
          ? html`<p class="export-info">${i18n.t("loading")}</p>`
          : nothing}
        ${this._exportError
          ? html`<div class="result-panel error" style="margin-top:12px">
              <h4>❌ ${i18n.t("error_loading")}</h4>
              <p>${this._exportError}</p>
            </div>`
          : nothing}
      </div>

      <!-- Import Section -->
      <div class="section">
        <div class="section-header">
          <span class="section-icon">📥</span>
          <h3>${i18n.t("import_csv")}</h3>
        </div>
        <dm-import-view></dm-import-view>
      </div>

      <!-- Danger Zone -->
      <div class="danger-zone">
        <h3>⚠️ ${i18n.t("maint_danger_zone")}</h3>
        <p>${i18n.t("maint_danger_desc")}</p>

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
          ? html` <div class="result-panel">
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
          ? html` <div class="result-panel error">
              <h4>❌ ${i18n.t("error_loading")}</h4>
              <p>${this._cleanError}</p>
            </div>`
          : nothing}
      </div>

      ${this._showConfirm ? this._renderConfirmDialog() : nothing}
    `;
  }

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

  // ------------------------------------------------------------------
  // Settings
  // ------------------------------------------------------------------

  private async _loadSettings() {
    try {
      const s = await this._settingsClient.getAll();
      this._settingsForm = { ...s };
    } catch (err) {
      console.error("Failed to load settings:", err);
    }
  }

  private _renderSettingsForm() {
    const f = this._settingsForm!;
    return html`
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
          <label>${i18n.t("config_mqtt_prefix")}</label>
          <input
            type="text"
            .value=${f.mqtt_topic_prefix}
            @input=${(e: Event) => this._updateSetting("mqtt_topic_prefix", e)}
          />
          <div class="hint">${i18n.t("config_mqtt_prefix_hint")}</div>
        </div>
        <div class="settings-field">
          <label>${i18n.t("config_default_home")}</label>
          <input
            type="text"
            .value=${f.default_home_name}
            @input=${(e: Event) => this._updateSetting("default_home_name", e)}
          />
          <div class="hint">${i18n.t("config_default_home_hint")}</div>
        </div>
      </div>
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
              >${this._settingsToast.msg}</span
            >`
          : nothing}
      </div>
    `;
  }

  private _updateSetting(key: keyof AppSettings, e: Event) {
    if (!this._settingsForm) return;
    this._settingsForm = {
      ...this._settingsForm,
      [key]: (e.target as HTMLInputElement).value,
    };
  }

  private async _saveSettings() {
    if (!this._settingsForm) return;
    this._settingsSaving = true;
    this._settingsToast = null;
    try {
      const result = await this._settingsClient.save(this._settingsForm);
      this._settingsForm = { ...result };
      // Refresh the global settings cache used by computed-fields etc.
      await refreshSettings();
      this._settingsToast = { msg: i18n.t("config_saved"), ok: true };
    } catch (err) {
      this._settingsToast = {
        msg: `${i18n.t("config_save_error")}: ${err}`,
        ok: false,
      };
    }
    this._settingsSaving = false;
    // Auto-hide toast after 4s
    setTimeout(() => {
      this._settingsToast = null;
    }, 4000);
  }
}
