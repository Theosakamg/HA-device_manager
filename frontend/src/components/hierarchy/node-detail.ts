/**
 * Node detail panel - shows info and children for the selected hierarchy node.
 */
import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import sharedStyles from "../../styles/shared.css?lit";
import nodeDetailStyles from "./node-detail.css?lit";
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
import { HierarchyClient } from "../../api/hierarchy-client";
import { showToast } from "../../utils/toast";
import { isValidSlug, isValidUrl } from "../../utils/validators";
import { getDoc } from "../../utils/doc-registry";
import { toSlug } from "../../utils/slug";
import {
  deviceLabel,
  computeHierarchyPrefixes,
} from "../../utils/computed-fields";
import "../shared/doc-block";

@localized
@customElement("dm-node-detail")
export class DmNodeDetail extends LitElement {
  static styles = [sharedStyles, nodeDetailStyles];

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
  @state() private _addingChild = false;
  @state() private _newChildName = "";
  @state() private _generatingGroups = false;
  @state() private _syncingFloors = false;
  @state() private _syncingRooms = false;
  @state() private _editFloorId: number | null = null;
  @state() private _editBuildingId: number | null = null;

  private _deviceClient = new DeviceClient();
  private _buildingClient = new BuildingClient();
  private _floorClient = new FloorClient();
  private _roomClient = new RoomClient();
  private _hierarchyClient = new HierarchyClient();

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
          <h2>${typeLabel}: ${this.node.name}</h2>
        </div>
        <div class="header-actions">
          <button
            class="btn btn-secondary"
            @click=${this._editing ? this._resetEdit : this._startEdit}
          >
            ${this._editing ? `↩ ${i18n.t("reset")}` : `✏️ ${i18n.t("edit")}`}
          </button>
          <div
            class="ha-sync-toolbar"
            role="toolbar"
            aria-label="HA sync actions"
          >
            <button
              class="btn btn-icon ha-sync-btn"
              ?disabled=${this._generatingGroups}
              @click=${this._generateHaGroups}
              aria-label=${i18n.t("ha_groups_generate")}
              data-tooltip=${this._generatingGroups
                ? i18n.t("ha_groups_generating")
                : i18n.t("ha_groups_generate")}
            >
              ${this._generatingGroups ? `⏳` : `🏠`}
            </button>
            <button
              class="btn btn-icon ha-sync-btn"
              ?disabled=${this._syncingFloors}
              @click=${this._syncHaFloors}
              aria-label=${i18n.t("ha_floors_sync")}
              data-tooltip=${this._syncingFloors
                ? i18n.t("ha_floors_syncing")
                : i18n.t("ha_floors_sync")}
            >
              ${this._syncingFloors ? `⏳` : `🏢`}
            </button>
            <button
              class="btn btn-icon ha-sync-btn"
              ?disabled=${this._syncingRooms}
              @click=${this._syncHaRooms}
              aria-label=${i18n.t("ha_rooms_sync")}
              data-tooltip=${this._syncingRooms
                ? i18n.t("ha_rooms_syncing")
                : i18n.t("ha_rooms_sync")}
            >
              ${this._syncingRooms ? `⏳` : `🚪`}
            </button>
          </div>
        </div>
      </div>

      <dm-doc-block
        .doc=${getDoc(`hierarchy.${this.node.type}.overview`)}
        storageKey="hierarchy-${this.node.type}"
      ></dm-doc-block>

      ${this._editing
        ? this._renderEditForm()
        : html`
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
              <span class="info-value"
                >${this._formatDate(this.node.createdAt)}</span
              >
              <span class="info-label">${i18n.t("updated_at")}</span>
              <span class="info-value"
                >${this._formatDate(this.node.updatedAt)}</span
              >
            </div>
            ${this._renderGeneratedFields(breadcrumb)}
            <div class="info-grid">
              ${this.node.type === "room"
                ? html`
                    <span class="info-label">${i18n.t("room_login")}</span>
                    <span class="info-value"
                      >${this._roomDetails?.login || "—"}</span
                    >
                    <span class="info-label">${i18n.t("room_password")}</span>
                    <span class="info-value info-value-flex">
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
          `}
      ${this.node.children.length > 0 ||
      this.node.type === "building" ||
      this.node.type === "floor"
        ? html`
            <div class="section-header">
              <h3>${this._childLabel()}</h3>
              <button
                class="btn btn-primary btn-sm"
                @click=${() => {
                  this._addingChild = true;
                  this._newChildName = "";
                }}
              >
                ${this.node.type === "building"
                  ? `+ ${i18n.t("add_floor")}`
                  : `+ ${i18n.t("add_room")}`}
              </button>
            </div>
            ${this._addingChild ? this._renderInlineChildAdd() : nothing}
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
              <button
                class="btn btn-primary btn-sm"
                @click=${() => {
                  window.location.hash = `#devices?create=room:${this.node!.id}`;
                }}
              >
                + ${i18n.t("add_device")}
              </button>
            </div>
            <dm-doc-block
              .doc=${getDoc("hierarchy.room.device_list")}
              storageKey="hierarchy-room-device-list"
            ></dm-doc-block>
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
                          <th>${i18n.t("device_position_name")}</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${this._devices.map(
                          (d) => html`
                            <tr
                              class="row-clickable"
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
                              <td>
                                <span class="device-name-label"
                                  >${deviceLabel(d)}</span
                                >
                                <span class="mac-label">${d.mac}</span>
                              </td>
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

  private _renderGeneratedFields(breadcrumb: HierarchyNode[]) {
    const slugs = breadcrumb.map((n) => n.slug);
    const fullName = breadcrumb.map((n) => n.name).join(" > ");
    const { mqttTopic, haEntityId } = computeHierarchyPrefixes(slugs);
    if (!mqttTopic) return nothing;
    return html`
      <div class="generated-fields">
        <h4 class="generated-fields-title">${i18n.t("generated_fields")}</h4>
        <div class="info-grid">
          <span class="info-label">${i18n.t("full_name")}</span>
          <code class="info-value info-value-code">${fullName}</code>
          <span class="info-label">${i18n.t("mqtt_topic")}</span>
          <code class="info-value info-value-code">${mqttTopic}</code>
          <span class="info-label">${i18n.t("ha_entity_id")}</span>
          <code class="info-value info-value-code">${haEntityId}</code>
        </div>
      </div>
    `;
  }

  private _renderInlineChildAdd() {
    const childType = this.node?.type === "building" ? "floor" : "room";
    return html`
      <div class="inline-add-row">
        <input
          type="text"
          class="inline-text-input"
          placeholder="${i18n.t("name")}"
          .value=${this._newChildName}
          @input=${(e: Event) => {
            this._newChildName = (e.target as HTMLInputElement).value;
          }}
          @keyup=${(e: KeyboardEvent) => {
            if (e.key === "Enter") this._confirmAddChild(childType);
            if (e.key === "Escape") this._addingChild = false;
          }}
        />
        <button
          class="btn btn-primary btn-sm"
          @click=${() => this._confirmAddChild(childType)}
        >
          ✓
        </button>
        <button
          class="btn btn-secondary btn-sm"
          @click=${() => {
            this._addingChild = false;
          }}
        >
          ✕
        </button>
      </div>
    `;
  }

  private async _confirmAddChild(type: string) {
    if (!this._newChildName.trim() || !this.node) return;
    const slug = toSlug(this._newChildName);
    try {
      if (type === "floor") {
        await this._floorClient.create({
          name: this._newChildName,
          slug,
          buildingId: this.node.id,
        });
      } else if (type === "room") {
        await this._roomClient.create({
          name: this._newChildName,
          slug,
          floorId: this.node.id,
        });
      }
      this._addingChild = false;
      this._newChildName = "";
      this.dispatchEvent(
        new CustomEvent("data-changed", { bubbles: true, composed: true })
      );
    } catch (err) {
      console.error(`Failed to create ${type}:`, err);
    }
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
              <div class="form-row form-row--mt">
                <div class="form-group">
                  <label>${i18n.t("parent_floor")}</label>
                  <select
                    @change=${(e: Event) => {
                      const v = (e.target as HTMLSelectElement).value;
                      this._editFloorId = v ? Number(v) : null;
                    }}
                  >
                    <option value="">—</option>
                    ${this._getAllFloors().map(
                      (f) =>
                        html`<option
                          value=${f.id}
                          ?selected=${f.id === this._editFloorId}
                        >
                          ${f.name}
                        </option>`
                    )}
                  </select>
                </div>
              </div>
              <div class="form-row form-row--mt">
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
                  <div class="info-value-flex">
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
        ${this.node?.type === "floor"
          ? html`
              <div class="form-row form-row--mt">
                <div class="form-group">
                  <label>${i18n.t("parent_building")}</label>
                  <select
                    @change=${(e: Event) => {
                      const v = (e.target as HTMLSelectElement).value;
                      this._editBuildingId = v ? Number(v) : null;
                    }}
                  >
                    <option value="">—</option>
                    ${(this.tree?.buildings ?? []).map(
                      (b) =>
                        html`<option
                          value=${b.id}
                          ?selected=${b.id === this._editBuildingId}
                        >
                          ${b.name}
                        </option>`
                    )}
                  </select>
                </div>
              </div>
            `
          : nothing}
        ${this._validationError
          ? html`<div class="validation-error">${this._validationError}</div>`
          : nothing}
        <div class="form-actions">
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
      this._editFloorId = this._findParentFloorId();
    } else if (this.node.type === "floor") {
      this._editBuildingId = this._findParentBuildingId();
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
      this._editFloorId = this._findParentFloorId();
    } else if (this.node.type === "floor") {
      this._editBuildingId = this._findParentBuildingId();
    }
  }

  /** Collect all floor nodes from the tree. */
  private _getAllFloors(): HierarchyNode[] {
    if (!this.tree) return [];
    return this.tree.buildings.flatMap((b) =>
      b.children.filter((n) => n.type === "floor")
    );
  }

  /** Find the parent floor id of the current room node by scanning the tree. */
  private _findParentFloorId(): number | null {
    if (!this.tree || !this.node || this.node.type !== "room") return null;
    for (const building of this.tree.buildings) {
      for (const floor of building.children) {
        for (const room of floor.children) {
          if (room.id === this.node.id) return floor.id;
        }
      }
    }
    return null;
  }

  /** Find the parent building id of the current floor node by scanning the tree. */
  private _findParentBuildingId(): number | null {
    if (!this.tree || !this.node || this.node.type !== "floor") return null;
    for (const building of this.tree.buildings) {
      for (const floor of building.children) {
        if (floor.id === this.node.id) return building.id;
      }
    }
    return null;
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
      if (this.node.type === "building") {
        const updated = await this._buildingClient.update(this.node.id, data);
        // Update node in-place with returned data
        this.node.name = updated.name;
        this.node.slug = updated.slug;
        this.node.description = updated.description ?? "";
        this.node.image = updated.image ?? "";
      } else if (this.node.type === "floor") {
        if (this._editBuildingId !== null)
          data.buildingId = this._editBuildingId;
        const updated = await this._floorClient.update(this.node.id, data);
        this.node.name = updated.name;
        this.node.slug = updated.slug;
        this.node.description = updated.description ?? "";
        this.node.image = updated.image ?? "";
      } else if (this.node.type === "room") {
        data.login = this._editLogin;
        data.password = this._editPassword;
        if (this._editFloorId !== null) data.floorId = this._editFloorId;
        const updated = await this._roomClient.update(this.node.id, data);
        this.node.name = updated.name;
        this.node.slug = updated.slug;
        this.node.description = updated.description ?? "";
        this.node.image = updated.image ?? "";
        // Update room details with returned data (avoids extra GET)
        this._roomDetails = updated;
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

  private async _generateHaGroups() {
    if (!this.node || this._generatingGroups) return;
    this._generatingGroups = true;
    try {
      const result = await this._hierarchyClient.generateHaGroups();
      if (result.total === 0) {
        showToast(i18n.t("ha_groups_success_none"), "info");
      } else {
        showToast(
          i18n.t("ha_groups_success").replace("{count}", String(result.total)),
          "success"
        );
      }
    } catch (err) {
      console.error("Failed to generate HA groups:", err);
      showToast(i18n.t("ha_groups_error"), "error");
    } finally {
      this._generatingGroups = false;
    }
  }

  private async _syncHaFloors() {
    if (this._syncingFloors) return;
    this._syncingFloors = true;
    try {
      const result = await this._hierarchyClient.syncHaFloors();
      if (result.total === 0) {
        showToast(i18n.t("ha_floors_sync_none"), "info");
      } else {
        showToast(
          i18n
            .t("ha_floors_sync_success")
            .replace("{count}", String(result.total)),
          "success"
        );
      }
    } catch (err) {
      console.error("Failed to sync HA floors:", err);
      showToast(i18n.t("ha_floors_sync_error"), "error");
    } finally {
      this._syncingFloors = false;
    }
  }

  private async _syncHaRooms() {
    if (this._syncingRooms) return;
    this._syncingRooms = true;
    try {
      const result = await this._hierarchyClient.syncHaRooms();
      if (result.total === 0) {
        showToast(i18n.t("ha_rooms_sync_none"), "info");
      } else {
        showToast(
          i18n
            .t("ha_rooms_sync_success")
            .replace("{count}", String(result.total)),
          "success"
        );
      }
    } catch (err) {
      console.error("Failed to sync HA rooms:", err);
      showToast(i18n.t("ha_rooms_sync_error"), "error");
    } finally {
      this._syncingRooms = false;
    }
  }
}
