/**
 * App shell component - main layout with navigation and routing.
 */
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../styles/shared-styles";
import { i18n, localized } from "../i18n";
import { loadSettings } from "../api/settings-client";
import "./hierarchy/hierarchy-view";
import "./settings/settings-view";
import "./devices/device-table";
import "./maintenance/maintenance-view";
import "./shared/toast-notification";
import type { DmToast } from "./shared/toast-notification";
import "./map/map-view";

type AppRoute = "hierarchy" | "devices" | "map" | "settings" | "maintenance";

@localized
@customElement("dm-app-shell")
export class DmAppShell extends LitElement {
  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        min-height: 100vh;
        background: var(--dm-bg);
      }
      .app-header {
        background: white;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
        padding: 0 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        height: 56px;
        position: sticky;
        top: 0;
        z-index: 100;
      }
      .app-title {
        font-size: 18px;
        font-weight: 600;
        color: var(--dm-text);
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .app-nav {
        display: flex;
        gap: 4px;
      }
      .nav-btn {
        padding: 8px 16px;
        border: none;
        background: transparent;
        cursor: pointer;
        font-size: 14px;
        border-radius: 4px;
        color: var(--dm-text-secondary);
        transition: all 0.15s;
      }
      .nav-btn:hover {
        background: rgba(0, 0, 0, 0.04);
        color: var(--dm-text);
      }
      .nav-btn.active {
        background: rgba(3, 169, 244, 0.1);
        color: var(--dm-primary);
        font-weight: 500;
      }
      .lang-toggle {
        padding: 4px 8px;
        border: 1px solid var(--dm-border);
        border-radius: 4px;
        background: transparent;
        cursor: pointer;
        font-size: 12px;
      }
      .app-content {
        padding: 24px;
      }
      @media (max-width: 768px) {
        .app-header {
          flex-wrap: wrap;
          height: auto;
          padding: 12px;
        }
        .app-nav {
          width: 100%;
          overflow-x: auto;
        }
        .app-content {
          padding: 12px;
        }
      }
    `,
  ];

  @state() private _route: AppRoute = "hierarchy";
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
    const fullHash = window.location.hash.replace("#", "") || "hierarchy";
    const route = fullHash.split("?")[0];
    const validRoutes: AppRoute[] = [
      "hierarchy",
      "devices",
      "map",
      "settings",
      "maintenance",
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
            class="nav-btn ${this._route === "maintenance" ? "active" : ""}"
            @click=${() => this._navigate("maintenance")}
          >
            🔧 ${i18n.t("nav_maintenance")}
          </button>
        </nav>
        <button class="lang-toggle" @click=${this._toggleLang}>
          ${this._lang === "fr" ? "🇬🇧 EN" : "🇫🇷 FR"}
        </button>
      </div>

      <main class="app-content">
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
        ${this._route === "maintenance"
          ? html`<dm-maintenance-view></dm-maintenance-view>`
          : ""}
      </main>

      <dm-toast></dm-toast>
    `;
  }
}
