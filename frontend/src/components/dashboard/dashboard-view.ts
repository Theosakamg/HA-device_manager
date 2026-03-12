/**
 * Dashboard view - overview with global statistics and charts.
 */
import { LitElement, html } from "lit";
import { customElement, state } from "lit/decorators.js";
import sharedStyles from "../../styles/shared.css?lit";
import dashboardStyles from "./dashboard.css?lit";
import { i18n, localized } from "../../i18n";
import { StatsClient } from "../../api/stats-client";
import type { StatEntry, DeploymentByGroup } from "../../api/stats-client";

interface StatItem {
  label: string;
  count: number;
  color: string;
  percentage: number;
}

interface DeploymentItem {
  label: string;
  total: number;
  success: number;
  fail: number;
  successRate: number;
  color: string;
}

@localized
@customElement("dm-dashboard-view")
export class DmDashboardView extends LitElement {
  static styles = [sharedStyles, dashboardStyles];

  @state() private _loading = true;
  @state() private _totalBuildings = 0;
  @state() private _totalFloors = 0;
  @state() private _totalRooms = 0;
  @state() private _totalDevices = 0;
  @state() private _byFirmware: StatItem[] = [];
  @state() private _byModel: StatItem[] = [];
  @state() private _deploymentTotal = 0;
  @state() private _deploymentSuccess = 0;
  @state() private _deploymentFail = 0;
  @state() private _deploymentByFirmware: DeploymentItem[] = [];
  @state() private _deploymentByModel: DeploymentItem[] = [];
  @state() private _expandedFirmware = false;
  @state() private _expandedModel = false;
  @state() private _expandedDeployFirmware = false;
  @state() private _expandedDeployModel = false;

  private _statsClient = new StatsClient();

  async connectedCallback() {
    super.connectedCallback();
    await this._loadData();
  }

  private async _loadData() {
    this._loading = true;
    try {
      const stats = await this._statsClient.getStats();
      this._totalBuildings = stats.buildings;
      this._totalFloors = stats.floors;
      this._totalRooms = stats.rooms;
      this._totalDevices = stats.devices;
      this._byFirmware = this._toStatItems(stats.byFirmware);
      this._byModel = this._toStatItems(stats.byModel);
      this._deploymentTotal = stats.deployment.total;
      this._deploymentSuccess = stats.deployment.success;
      this._deploymentFail = stats.deployment.fail;
      this._deploymentByFirmware = this._toDeploymentItems(
        stats.deploymentByFirmware
      );
      this._deploymentByModel = this._toDeploymentItems(
        stats.deploymentByModel
      );
    } catch (err) {
      console.error("Dashboard: failed to load stats", err);
    }
    this._loading = false;
  }

  private _toStatItems(entries: StatEntry[]): StatItem[] {
    const max = entries[0]?.count ?? 1;
    return entries.map((entry, i) => ({
      label: entry.name,
      count: entry.count,
      color: `color-${i % 10}`,
      percentage: Math.round((entry.count / max) * 100),
    }));
  }

  private _toDeploymentItems(entries: DeploymentByGroup[]): DeploymentItem[] {
    return entries.map((entry, i) => ({
      label: entry.name,
      total: entry.total,
      success: entry.success,
      fail: entry.fail,
      successRate:
        entry.total > 0 ? Math.round((entry.success / entry.total) * 100) : 0,
      color: `color-${i % 10}`,
    }));
  }

  private _renderKpi(
    icon: string,
    value: number,
    label: string,
    colorClass: string
  ) {
    return html`
      <div class="kpi-card ${colorClass}">
        <div class="kpi-icon">${icon}</div>
        <div class="kpi-body">
          ${this._loading
            ? html`<div class="skeleton-kpi"></div>`
            : html`<div class="kpi-value">${value}</div>`}
          <div class="kpi-label">${label}</div>
        </div>
      </div>
    `;
  }

  private _renderBarChart(
    title: string,
    icon: string,
    items: StatItem[],
    expanded: boolean,
    onToggle: () => void
  ) {
    const displayItems = expanded ? items : items.slice(0, 4);
    const hasMore = items.length > 4;

    return html`
      <div class="chart-card">
        <div class="chart-title">${icon} ${title}</div>
        ${this._loading
          ? html`
              <div class="loading-skeleton">
                ${[80, 60, 45, 30].map(
                  (w) =>
                    html`<div class="skeleton-bar" style="width:${w}%"></div>`
                )}
              </div>
            `
          : items.length === 0
            ? html`<div class="empty-chart">${i18n.t("no_devices")}</div>`
            : html`
                <div class="bar-list">
                  ${displayItems.map(
                    (item) => html`
                      <div class="bar-row">
                        <span class="bar-label" title="${item.label}"
                          >${item.label}</span
                        >
                        <div class="bar-track">
                          <div
                            class="bar-fill ${item.color}"
                            style="width: ${item.percentage}%"
                          ></div>
                        </div>
                        <span class="bar-count">${item.count}</span>
                      </div>
                    `
                  )}
                </div>
                ${hasMore
                  ? html`
                      <button
                        class="btn btn-secondary btn-show-more"
                        @click=${onToggle}
                      >
                        ${expanded
                          ? `▲ ${i18n.t("dashboard_show_less")}`
                          : `▼ ${i18n.t("dashboard_show_more")} (${items.length - 4})`}
                      </button>
                    `
                  : ""}
              `}
      </div>
    `;
  }

  private _renderDeploymentChart(
    title: string,
    icon: string,
    items: DeploymentItem[],
    expanded: boolean,
    onToggle: () => void
  ) {
    const displayItems = expanded ? items : items.slice(0, 4);
    const hasMore = items.length > 4;

    return html`
      <div class="chart-card">
        <div class="chart-title">${icon} ${title}</div>
        ${this._loading
          ? html`
              <div class="loading-skeleton">
                ${[80, 60, 45, 30].map(
                  (w) =>
                    html`<div class="skeleton-bar" style="width:${w}%"></div>`
                )}
              </div>
            `
          : items.length === 0
            ? html`<div class="empty-chart">${i18n.t("no_devices")}</div>`
            : html`
                <div class="bar-list">
                  ${displayItems.map(
                    (item) => html`
                      <div class="bar-row">
                        <span
                          class="bar-label"
                          title="${item.label} - ${item.success}/${item.total} (${item.successRate}%)"
                          >${item.label}</span
                        >
                        <div class="bar-track">
                          <div
                            class="bar-fill"
                            style="width: ${item.successRate}%; background: #4caf50;"
                          ></div>
                        </div>
                        <span class="bar-count"
                          >${item.success}/${item.total}
                          (${item.successRate}%)</span
                        >
                      </div>
                    `
                  )}
                </div>
                ${hasMore
                  ? html`
                      <button
                        class="btn btn-secondary btn-show-more"
                        @click=${onToggle}
                      >
                        ${expanded
                          ? `▲ ${i18n.t("dashboard_show_less")}`
                          : `▼ ${i18n.t("dashboard_show_more")} (${items.length - 4})`}
                      </button>
                    `
                  : ""}
              `}
      </div>
    `;
  }

  render() {
    const now = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });

    return html`
      <div class="page-header">
        <h1 class="page-title">📊 ${i18n.t("dashboard_title")}</h1>
        <p class="page-subtitle">${i18n.t("dashboard_subtitle")}</p>
      </div>

      <!-- KPI Cards -->
      <div class="kpi-grid">
        ${this._renderKpi(
          "🏢",
          this._totalBuildings,
          i18n.t("buildings"),
          "blue"
        )}
        ${this._renderKpi("🏗️", this._totalFloors, i18n.t("floors"), "teal")}
        ${this._renderKpi("🚪", this._totalRooms, i18n.t("rooms"), "purple")}
        ${this._renderKpi(
          "📱",
          this._totalDevices,
          i18n.t("devices"),
          "orange"
        )}
      </div>

      <!-- Distribution Charts -->
      <div class="charts-grid">
        ${this._renderBarChart(
          i18n.t("dashboard_by_firmware"),
          "💾",
          this._byFirmware,
          this._expandedFirmware,
          () => (this._expandedFirmware = !this._expandedFirmware)
        )}
        ${this._renderBarChart(
          i18n.t("dashboard_by_hardware"),
          "🔧",
          this._byModel,
          this._expandedModel,
          () => (this._expandedModel = !this._expandedModel)
        )}
      </div>

      <!-- Deployment Statistics -->
      <div class="deploy-section">
        <h2 class="deploy-section-title">
          🚀 ${i18n.t("dashboard_deployment_title")}
        </h2>

        <!-- Deployment KPI Cards -->
        <div class="kpi-grid kpi-grid--3">
          ${this._renderKpi(
            "📦",
            this._deploymentTotal,
            i18n.t("dashboard_deployment_total"),
            "blue"
          )}
          ${this._renderKpi(
            "✅",
            this._deploymentSuccess,
            i18n.t("dashboard_deployment_success"),
            "teal"
          )}
          ${this._renderKpi(
            "❌",
            this._deploymentFail,
            i18n.t("dashboard_deployment_fail"),
            "purple"
          )}
        </div>

        <!-- Deployment Charts -->
        <div class="charts-grid charts-grid--mt">
          ${this._renderDeploymentChart(
            i18n.t("dashboard_deployment_by_firmware"),
            "💾",
            this._deploymentByFirmware,
            this._expandedDeployFirmware,
            () => (this._expandedDeployFirmware = !this._expandedDeployFirmware)
          )}
          ${this._renderDeploymentChart(
            i18n.t("dashboard_deployment_by_hardware"),
            "🔧",
            this._deploymentByModel,
            this._expandedDeployModel,
            () => (this._expandedDeployModel = !this._expandedDeployModel)
          )}
        </div>
      </div>

      <p class="refresh-hint">
        ${i18n.t("dashboard_last_refresh")} ${now}
        <button
          class="btn btn-secondary btn-refresh btn-sm"
          @click=${this._loadData}
        >
          ↻ ${i18n.t("dashboard_refresh")}
        </button>
      </p>
    `;
  }
}
