/**
 * Node detail panel - shows info and children for the selected hierarchy node.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";
import type {
  HierarchyNode,
  HierarchyTree,
  DmDevice,
} from "../../types/device";
import type { DmRoom } from "../../types/room";
import { DeviceClient } from "../../api/device-client";
import { BuildingClient } from "../../api/building-client";
import { FloorClient } from "../../api/floor-client";
import { RoomClient } from "../../api/room-client";
import { showToast } from "../../utils/toast";
import { isValidSlug, isValidUrl } from "../../utils/validators";

@localized
@customElement("dm-node-detail")
export class DmNodeDetail extends LitElement {
  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
      }
      .info-grid {
        display: grid;
        grid-template-columns: 120px 1fr;
        gap: 8px;
        margin-bottom: 16px;
      }
      .info-label {
        font-weight: 500;
        color: var(--dm-text-secondary);
        font-size: 13px;
      }
      .info-value {
        font-size: 14px;
      }
      .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin: 16px 0 8px;
      }
      .children-list {
        display: grid;
        gap: 8px;
      }
      .child-card {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 14px;
        border: 1px solid var(--dm-border);
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.15s;
      }
      .child-card:hover {
        background: rgba(0, 0, 0, 0.02);
      }
      .child-info {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .device-row {
        padding: 8px 12px;
        border-bottom: 1px solid var(--dm-border);
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .edit-form {
        margin: 16px 0;
        padding: 16px;
        border: 1px solid var(--dm-border);
        border-radius: 6px;
      }
      .breadcrumb {
        display: flex;
        align-items: center;
        gap: 4px;
        flex-wrap: wrap;
        font-size: 13px;
        color: var(--dm-text-secondary);
        margin-bottom: 4px;
      }
      .breadcrumb-sep {
        opacity: 0.5;
      }
      .breadcrumb-item {
        background: none;
        border: none;
        padding: 0;
        cursor: pointer;
        color: var(--dm-text-secondary);
        font-size: 13px;
        text-decoration: underline;
      }
      .breadcrumb-item:hover {
        color: var(--dm-primary);
      }
      .breadcrumb-current {
        font-weight: 600;
        color: var(--dm-text);
      }
      .validation-error {
        color: #f44336;
        font-size: 13px;
        margin-bottom: 8px;
      }
    `,
  ];

  @property({ type: Object }) node: HierarchyNode | null = null;
  @property({ type: Object }) tree: HierarchyTree | null = null;

  @state() private _devices: DmDevice[] = [];
  @state() private _loadingDevices = false;
  @state() private _roomDetails: DmRoom | null = null;
  @state() private _editing = false;
  @state() private _editName = "";
  @state() private _editSlug = "";
  @state() private _editDescription = "";
  @state() private _editImage = "";
  @state() private _editLogin = "";
  @state() private _editPassword = "";
  @state() private _showPassword = false;
  @state() private _validationError = "";

  private _deviceClient = new DeviceClient();
  private _buildingClient = new BuildingClient();
  private _floorClient = new FloorClient();
  private _roomClient = new RoomClient();

  updated(changedProperties: Map<string, unknown>) {
    if (changedProperties.has("node") && this.node) {
      this._editing = false;
      this._showPassword = false;
      if (this.node.type === "room") {
        this._loadDevices();
        this._loadRoomDetails();
      } else {
        this._devices = [];
        this._roomDetails = null;
      }
    }
  }

  private async _loadDevices() {
    if (!this.node || this.node.type !== "room") return;
    this._loadingDevices = true;
    try {
      this._devices = await this._deviceClient.getAll(this.node.id);
    } catch (err) {
      console.error("Failed to load devices:", err);
    }
    this._loadingDevices = false;
  }

  private async _loadRoomDetails() {
    if (!this.node || this.node.type !== "room") return;
    try {
      this._roomDetails = await this._roomClient.getById(this.node.id);
    } catch (err) {
      console.error("Failed to load room details:", err);
      this._roomDetails = null;
    }
  }

  private _buildBreadcrumb(): HierarchyNode[] {
    if (!this.tree || !this.node) return [];
    for (const building of this.tree.buildings) {
      if (building.id === this.node.id && building.type === this.node.type)
        return [building];
      for (const floor of building.children) {
        if (floor.id === this.node.id && floor.type === this.node.type)
          return [building, floor];
        for (const room of floor.children) {
          if (room.id === this.node.id && room.type === this.node.type)
            return [building, floor, room];
        }
      }
    }
    return [this.node];
  }

  private _validateEditFields(): string | null {
    if (!this._editName.trim()) return i18n.t("validation_name_required");
    if (!this._editSlug.trim()) return i18n.t("validation_slug_required");
    if (!isValidSlug(this._editSlug)) return i18n.t("validation_slug_format");
    if (!isValidUrl(this._editImage)) return i18n.t("validation_url_format");
    return null;
  }

  render() {
    if (!this.node)
      return html`<div class="empty-state">${i18n.t("no_buildings")}</div>`;

    const typeLabel = i18n.t(this.node.type);
    const breadcrumb = this._buildBreadcrumb();
    return html`
      <div class="card-header">
        <div>
          ${breadcrumb.length > 1
            ? html`<nav class="breadcrumb">
                ${breadcrumb.map((n, idx) =>
                  idx < breadcrumb.length - 1
                    ? html`<button
                          class="breadcrumb-item"
                          @click=${() => this._selectChild(n)}
                        >
                          ${n.name}</button
                        ><span class="breadcrumb-sep">›</span>`
                    : html`<span class="breadcrumb-current">${n.name}</span>`
                )}
              </nav>`
            : nothing}
          <h2 style="margin:0">${typeLabel}: ${this.node.name}</h2>
        </div>
        <div>
          <button
            class="btn btn-secondary"
            @click=${this._editing ? this._resetEdit : this._startEdit}
          >
            ${this._editing ? `↩ ${i18n.t("reset")}` : `✏️ ${i18n.t("edit")}`}
          </button>
        </div>
      </div>

      ${this._editing ? this._renderEditForm() : nothing}

      <div class="info-grid">
        <span class="info-label">${i18n.t("name")}</span>
        <span class="info-value">${this.node.name}</span>
        <span class="info-label">${i18n.t("slug")}</span>
        <span class="info-value">${this.node.slug}</span>
        <span class="info-label">${i18n.t("description")}</span>
        <span class="info-value">${this.node.description || "—"}</span>
        <span class="info-label">${i18n.t("image")}</span>
        <span class="info-value">${this.node.image || "—"}</span>
        <span class="info-label">${i18n.t("device_count")}</span>
        <span class="info-value">${this.node.deviceCount}</span>
        <span class="info-label">${i18n.t("created_at")}</span>
        <span class="info-value">${this._formatDate(this.node.createdAt)}</span>
        <span class="info-label">${i18n.t("updated_at")}</span>
        <span class="info-value">${this._formatDate(this.node.updatedAt)}</span>
        ${this.node.type === "room"
          ? html`
              <span class="info-label">${i18n.t("room_login")}</span>
              <span class="info-value">${this._roomDetails?.login || "—"}</span>
              <span class="info-label">${i18n.t("room_password")}</span>
              <span
                class="info-value"
                style="display:flex; align-items:center; gap:6px;"
              >
                ${this._roomDetails?.password
                  ? this._showPassword
                    ? this._roomDetails.password
                    : "••••••••"
                  : "—"}
                ${this._roomDetails?.password
                  ? html`
                      <button
                        class="btn-icon"
                        title=${this._showPassword
                          ? i18n.t("hide_password")
                          : i18n.t("show_password")}
                        @click=${() => {
                          this._showPassword = !this._showPassword;
                        }}
                      >
                        ${this._showPassword ? "🙈" : "👁"}
                      </button>
                    `
                  : nothing}
              </span>
            `
          : nothing}
      </div>

      ${this.node.children.length > 0
        ? html`
            <div class="section-header">
              <h3>${this._childLabel()}</h3>
            </div>
            <div class="children-list">
              ${this.node.children.map(
                (child) => html`
                  <div
                    class="child-card"
                    @click=${() => this._selectChild(child)}
                  >
                    <div class="child-info">
                      <span>${this._childIcon(child.type)} ${child.name}</span>
                    </div>
                    <span class="badge"
                      >${child.deviceCount} ${i18n.t("device_count")}</span
                    >
                  </div>
                `
              )}
            </div>
          `
        : nothing}
      ${this.node.type === "room"
        ? html`
            <div class="section-header">
              <h3>${i18n.t("devices")} (${this._devices.length})</h3>
            </div>
            ${this._loadingDevices
              ? html`<div class="loading">${i18n.t("loading")}</div>`
              : this._devices.length === 0
                ? html`<div class="empty-state">
                    ${i18n.t("no_devices_in_room")}
                  </div>`
                : html`
                    <table>
                      <thead>
                        <tr>
                          <th></th>
                          <th>MAC</th>
                          <th>${i18n.t("device_function")}</th>
                          <th>${i18n.t("device_position_name")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${this._devices.map(
                          (d) => html`
                            <tr
                              style="cursor:pointer"
                              @click=${() => {
                                window.location.hash = `#devices?filter=${encodeURIComponent(d.mac)}`;
                              }}
                            >
                              <td class="enabled-dot">
                                <span
                                  class="status-dot ${d.enabled
                                    ? "status-enabled"
                                    : "status-disabled"}"
                                ></span>
                              </td>
                              <td style="font-family:monospace;font-size:12px">
                                ${d.mac}
                              </td>
                              <td>${d.functionName || "—"}</td>
                              <td>${d.positionName}</td>
                            </tr>
                          `
                        )}
                      </tbody>
                    </table>
                  `}
          `
        : nothing}
    `;
  }

  private _renderEditForm() {
    return html`
      <div class="edit-form">
        <div class="form-row">
          <div class="form-group">
            <label>${i18n.t("name")}</label>
            <input
              type="text"
              .value=${this._editName}
              @input=${(e: Event) => {
                this._editName = (e.target as HTMLInputElement).value;
              }}
            />
          </div>
          <div class="form-group">
            <label>${i18n.t("slug")}</label>
            <input
              type="text"
              .value=${this._editSlug}
              @input=${(e: Event) => {
                this._editSlug = (e.target as HTMLInputElement).value;
              }}
            />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>${i18n.t("description")}</label>
            <input
              type="text"
              .value=${this._editDescription}
              @input=${(e: Event) => {
                this._editDescription = (e.target as HTMLInputElement).value;
              }}
            />
          </div>
          <div class="form-group">
            <label>${i18n.t("image")}</label>
            <input
              type="text"
              .value=${this._editImage}
              placeholder="URL or path"
              @input=${(e: Event) => {
                this._editImage = (e.target as HTMLInputElement).value;
              }}
            />
          </div>
        </div>
        ${this.node?.type === "room"
          ? html`
              <div class="form-row" style="margin-top:8px;">
                <div class="form-group">
                  <label>${i18n.t("room_login")}</label>
                  <input
                    type="text"
                    .value=${this._editLogin}
                    @input=${(e: Event) => {
                      this._editLogin = (e.target as HTMLInputElement).value;
                    }}
                  />
                </div>
                <div class="form-group">
                  <label>${i18n.t("room_password")}</label>
                  <div style="display:flex; align-items:center; gap:6px;">
                    <input
                      type=${this._showPassword ? "text" : "password"}
                      .value=${this._editPassword}
                      @input=${(e: Event) => {
                        this._editPassword = (
                          e.target as HTMLInputElement
                        ).value;
                      }}
                    />
                    <button
                      type="button"
                      class="btn-icon"
                      title=${this._showPassword
                        ? i18n.t("hide_password")
                        : i18n.t("show_password")}
                      @click=${() => {
                        this._showPassword = !this._showPassword;
                      }}
                    >
                      ${this._showPassword ? "🙈" : "👁"}
                    </button>
                  </div>
                </div>
              </div>
            `
          : nothing}
        ${this._validationError
          ? html`<div class="validation-error">${this._validationError}</div>`
          : nothing}
        <div style="display:flex; gap:8px; margin-top:8px;">
          <button class="btn btn-primary" @click=${this._saveEdit}>
            ${i18n.t("save")}
          </button>
          <button
            class="btn btn-secondary"
            @click=${() => {
              this._editing = false;
            }}
          >
            ${i18n.t("cancel")}
          </button>
        </div>
      </div>
    `;
  }

  private _startEdit() {
    if (!this.node) return;
    this._validationError = "";
    this._editName = this.node.name;
    this._editSlug = this.node.slug;
    this._editDescription = this.node.description || "";
    this._editImage = this.node.image || "";
    if (this.node.type === "room") {
      this._editLogin = this._roomDetails?.login || "";
      this._editPassword = this._roomDetails?.password || "";
      this._showPassword = false;
    }
    this._editing = true;
  }

  private _resetEdit() {
    if (!this.node) return;
    this._validationError = "";
    this._editName = this.node.name;
    this._editSlug = this.node.slug;
    this._editDescription = this.node.description || "";
    this._editImage = this.node.image || "";
    if (this.node.type === "room") {
      this._editLogin = this._roomDetails?.login || "";
      this._editPassword = this._roomDetails?.password || "";
    }
  }

  private async _saveEdit() {
    if (!this.node) return;
    this._validationError = "";
    const validationErr = this._validateEditFields();
    if (validationErr) {
      this._validationError = validationErr;
      return;
    }
    try {
      const data: Record<string, unknown> = {
        name: this._editName,
        slug: this._editSlug,
        description: this._editDescription,
        image: this._editImage,
      };
      if (this.node.type === "building")
        await this._buildingClient.update(this.node.id, data);
      else if (this.node.type === "floor")
        await this._floorClient.update(this.node.id, data);
      else if (this.node.type === "room") {
        data.login = this._editLogin;
        data.password = this._editPassword;
        await this._roomClient.update(this.node.id, data);
        await this._loadRoomDetails();
      }
      this._editing = false;
      showToast(i18n.t("success_updated"), "success");
      this.dispatchEvent(
        new CustomEvent("data-changed", { bubbles: true, composed: true })
      );
    } catch (err) {
      console.error("Failed to update node:", err);
      showToast(i18n.t("error_saving"), "error");
    }
  }

  private _selectChild(child: HierarchyNode) {
    // Emit node-selected so hierarchy-view updates the selected node
    this.dispatchEvent(
      new CustomEvent("node-selected", {
        detail: { node: child },
        bubbles: true,
        composed: true,
      })
    );
    // Also emit expand-to-node so the tree auto-expands and highlights the child
    this.dispatchEvent(
      new CustomEvent("expand-to-node", {
        detail: { node: child },
        bubbles: true,
        composed: true,
      })
    );
  }

  /** Format an ISO date string for display. */
  private _formatDate(dateStr?: string): string {
    if (!dateStr) return "—";
    try {
      const d = new Date(dateStr);
      return d.toLocaleString();
    } catch {
      return dateStr;
    }
  }

  private _childLabel(): string {
    if (!this.node) return "";
    if (this.node.type === "building") return i18n.t("floors");
    if (this.node.type === "floor") return i18n.t("rooms");
    return "";
  }

  private _childIcon(type: string): string {
    if (type === "floor") return "🏢";
    if (type === "room") return "🚪";
    return "📦";
  }
}
