/**
 * App shell component - main layout with navigation and routing.
 */
import { LitElement, html } from "lit";
import { customElement, state } from "lit/decorators.js";
import sharedStyles from "../styles/shared.css?lit";
import appShellStyles from "./app-shell.css?lit";
import { i18n, localized } from "../i18n";
import { loadSettings } from "../api/settings-client";
import "./dashboard/dashboard-view";
import "./hierarchy/hierarchy-view";
import "./settings/settings-view";
import "./devices/device-table";
import "./system/system-view";
import "./shared/toast-notification";
import type { DmToast } from "./shared/toast-notification";
import "./map/map-view";
import "./activity-log/activity-log-view";

type AppRoute =
  | "dashboard"
  | "hierarchy"
  | "devices"
  | "map"
  | "settings"
  | "system"
  | "activity_log";

@localized
@customElement("dm-app-shell")
export class DmAppShell extends LitElement {
  static styles = [sharedStyles, appShellStyles];

  @state() private _route: AppRoute = "dashboard";
  @state() private _lang: string = i18n.getCurrentLanguage();

  connectedCallback() {
    super.connectedCallback();
    this._route = this._getRouteFromHash();
    window.addEventListener("hashchange", this._onHashChange);
    window.addEventListener("show-toast", this._onShowToast);
    // Pre-load user settings so computed fields use the right values.
    loadSettings().catch((err) =>
      console.warn("Failed to pre-load settings:", err)
    );
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener("hashchange", this._onHashChange);
    window.removeEventListener("show-toast", this._onShowToast);
  }

  private _onShowToast = (e: Event) => {
    const { message, type, duration } = (e as CustomEvent).detail;
    const toast = this.shadowRoot?.querySelector<DmToast>("dm-toast");
    toast?.show(message, type, duration);
  };

  private _onHashChange = () => {
    this._route = this._getRouteFromHash();
  };

  private _getRouteFromHash(): AppRoute {
    const fullHash = window.location.hash.replace("#", "") || "dashboard";
    const route = fullHash.split("?")[0];
    const validRoutes: AppRoute[] = [
      "dashboard",
      "hierarchy",
      "devices",
      "map",
      "settings",
      "system",
      "activity_log",
    ];
    return validRoutes.includes(route as AppRoute)
      ? (route as AppRoute)
      : "hierarchy";
  }

  private _navigate(route: AppRoute) {
    window.location.hash = `#${route}`;
  }

  private _toggleLang() {
    const newLang = this._lang === "en" ? "fr" : "en";
    i18n.setLanguage(newLang);
    this._lang = newLang;
    this.requestUpdate();
  }

  render() {
    return html`
      <div class="app-header">
        <div class="app-title">
          <span>🏠</span>
          <span>Device Manager</span>
        </div>
        <nav class="app-nav">
          <button
            class="nav-btn ${this._route === "dashboard" ? "active" : ""}"
            @click=${() => this._navigate("dashboard")}
          >
            📊 ${i18n.t("nav_dashboard")}
          </button>
          <button
            class="nav-btn ${this._route === "hierarchy" ? "active" : ""}"
            @click=${() => this._navigate("hierarchy")}
          >
            🏗️ ${i18n.t("nav_hierarchy")}
          </button>
          <button
            class="nav-btn ${this._route === "devices" ? "active" : ""}"
            @click=${() => this._navigate("devices")}
          >
            📱 ${i18n.t("nav_devices")}
          </button>
          <button
            class="nav-btn ${this._route === "map" ? "active" : ""}"
            @click=${() => this._navigate("map")}
          >
            🗺️ ${i18n.t("nav_map")}
          </button>
          <button
            class="nav-btn ${this._route === "settings" ? "active" : ""}"
            @click=${() => this._navigate("settings")}
          >
            ⚙️ ${i18n.t("nav_settings")}
          </button>
          <button
            class="nav-btn ${this._route === "system" ? "active" : ""}"
            @click=${() => this._navigate("system")}
          >
            🖥️ ${i18n.t("nav_system")}
          </button>
          <button
            class="nav-btn ${this._route === "activity_log" ? "active" : ""}"
            @click=${() => this._navigate("activity_log")}
          >
            📋 ${i18n.t("nav_activity_log")}
          </button>
        </nav>
        <button class="lang-toggle" @click=${this._toggleLang}>
          ${this._lang === "fr" ? "🇬🇧 EN" : "🇫🇷 FR"}
        </button>
      </div>

      <main class="app-content">
        ${this._route === "dashboard"
          ? html`<dm-dashboard-view></dm-dashboard-view>`
          : ""}
        ${this._route === "hierarchy"
          ? html`<dm-hierarchy-view></dm-hierarchy-view>`
          : ""}
        ${this._route === "devices"
          ? html`<dm-device-table></dm-device-table>`
          : ""}
        ${this._route === "map" ? html`<dm-map-view></dm-map-view>` : ""}
        ${this._route === "settings"
          ? html`<dm-settings-view></dm-settings-view>`
          : ""}
        ${this._route === "system"
          ? html`<dm-system-view></dm-system-view>`
          : ""}
        ${this._route === "activity_log"
          ? html`<dm-activity-log-view></dm-activity-log-view>`
          : ""}
      </main>

      <dm-toast></dm-toast>
    `;
  }
}
