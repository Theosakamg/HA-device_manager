/**
 * Settings view with tabs for managing reference entities.
 */
import { LitElement, html } from "lit";
import { customElement, state } from "lit/decorators.js";
import sharedStyles from "../../styles/shared.css?lit";
import settingsViewStyles from "./settings-view.css?lit";
import { i18n, localized } from "../../i18n";
import { getDoc } from "../../utils/doc-registry";
import { DeviceModelClient } from "../../api/device-model-client";
import { DeviceFirmwareClient } from "../../api/device-firmware-client";
import { DeviceFunctionClient } from "../../api/device-function-client";
import { StatsClient } from "../../api/stats-client";
import type { CrudConfig } from "../shared/crud-table";
import "./crud-tab";
import "../shared/doc-block";

/** Navigate to devices view filtered by a setting name.
 * Uses the Excel column filter (cfilters) when a colKey is provided.
 */
function navigateToDevicesWithFilter(value: string, colKey?: string) {
  if (colKey) {
    const cfilters = JSON.stringify({ [colKey]: [value] });
    window.location.hash = `#devices?cfilters=${encodeURIComponent(cfilters)}`;
  } else {
    window.location.hash = `#devices?filter=${encodeURIComponent(value)}`;
  }
}

type SettingsTab = "models" | "firmwares" | "functions";

const _modelClient = new DeviceModelClient();
const _firmwareClient = new DeviceFirmwareClient();
const _functionClient = new DeviceFunctionClient();
const _statsClient = new StatsClient();

@localized
@customElement("dm-settings-view")
export class DmSettingsView extends LitElement {
  static styles = [sharedStyles, settingsViewStyles];

  @state() private _activeTab: SettingsTab = "models";
  @state() private _modelCount = 0;
  @state() private _firmwareCount = 0;
  @state() private _functionCount = 0;

  async connectedCallback() {
    super.connectedCallback();
    await this._loadCounts();
  }

  private async _loadCounts() {
    try {
      const stats = await _statsClient.getStats();
      this._modelCount = stats.settingsCounts.models;
      this._firmwareCount = stats.settingsCounts.firmwares;
      this._functionCount = stats.settingsCounts.functions;
    } catch {
      // Counts stay at 0 on error
    }
  }

  /** Refresh counts when a crud-tab saves or deletes. */
  private async _onCrudChange() {
    // Small delay to let the crud-tab reload first
    setTimeout(() => this._loadCounts(), 300);
  }

  private get _modelConfig(): CrudConfig {
    return {
      entityName: i18n.t("tab_models"),
      description: getDoc("settings.models.overview"),
      filterDevicesKey: "name",
      filterDevicesColKey: "refs.modelName",
      columns: [
        {
          key: "name",
          label: i18n.t("model_name"),
          type: "text",
          editable: true,
        },
        {
          key: "template",
          label: i18n.t("model_template"),
          type: "text",
          editable: true,
        },
        {
          key: "enabled",
          label: i18n.t("enabled"),
          type: "boolean",
          editable: true,
        },
      ],
    };
  }

  private get _firmwareConfig(): CrudConfig {
    return {
      entityName: i18n.t("tab_firmwares"),
      description: getDoc("settings.firmwares.overview"),
      filterDevicesKey: "name",
      filterDevicesColKey: "refs.firmwareName",
      columns: [
        {
          key: "name",
          label: i18n.t("firmware_name"),
          type: "text",
          editable: true,
        },
        {
          key: "deployable",
          label: i18n.t("firmware_deployable"),
          type: "boolean",
          editable: true,
        },
        {
          key: "enabled",
          label: i18n.t("enabled"),
          type: "boolean",
          editable: true,
        },
      ],
    };
  }

  private get _functionConfig(): CrudConfig {
    return {
      entityName: i18n.t("tab_functions"),
      description: getDoc("settings.functions.overview"),
      filterDevicesKey: "name",
      filterDevicesColKey: "refs.functionName",
      columns: [
        {
          key: "name",
          label: i18n.t("function_name"),
          type: "text",
          editable: true,
        },
        {
          key: "enabled",
          label: i18n.t("enabled"),
          type: "boolean",
          editable: true,
        },
      ],
    };
  }

  render() {
    return html`
      <div class="settings-container">
        <h2>${i18n.t("settings_title")}</h2>
        <dm-doc-block
          .doc=${getDoc("settings.overview")}
          storageKey="settings-overview"
        ></dm-doc-block>

        <div class="tabs">
          <button
            class="tab ${this._activeTab === "models" ? "active" : ""}"
            @click=${() => {
              this._activeTab = "models";
            }}
          >
            ${i18n.t("tab_models")}
            <span class="tab-badge">${this._modelCount}</span>
          </button>
          <button
            class="tab ${this._activeTab === "firmwares" ? "active" : ""}"
            @click=${() => {
              this._activeTab = "firmwares";
            }}
          >
            ${i18n.t("tab_firmwares")}
            <span class="tab-badge">${this._firmwareCount}</span>
          </button>
          <button
            class="tab ${this._activeTab === "functions" ? "active" : ""}"
            @click=${() => {
              this._activeTab = "functions";
            }}
          >
            ${i18n.t("tab_functions")}
            <span class="tab-badge">${this._functionCount}</span>
          </button>
        </div>

        <div
          @crud-filter=${(e: CustomEvent) =>
            navigateToDevicesWithFilter(e.detail.value, e.detail.colKey)}
          @crud-save=${() => this._onCrudChange()}
          @crud-delete=${() => this._onCrudChange()}
        >
          ${this._activeTab === "models"
            ? html`<dm-crud-tab
                .client=${_modelClient}
                .config=${this._modelConfig}
              ></dm-crud-tab>`
            : ""}
          ${this._activeTab === "firmwares"
            ? html`<dm-crud-tab
                .client=${_firmwareClient}
                .config=${this._firmwareConfig}
              ></dm-crud-tab>`
            : ""}
          ${this._activeTab === "functions"
            ? html`<dm-crud-tab
                .client=${_functionClient}
                .config=${this._functionConfig}
              ></dm-crud-tab>`
            : ""}
        </div>
      </div>
    `;
  }
}
