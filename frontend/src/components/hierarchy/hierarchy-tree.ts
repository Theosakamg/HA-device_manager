/**
 * Hierarchy tree component - collapsible tree of Building > Floor > Room.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";
import type { HierarchyTree, HierarchyNode } from "../../types/device";
import { BuildingClient } from "../../api/building-client";
import { FloorClient } from "../../api/floor-client";
import { RoomClient } from "../../api/room-client";
import { toSlug } from "../../utils/slug";
import "../shared/confirm-dialog";

@localized
@customElement("dm-hierarchy-tree")
export class DmHierarchyTreeComponent extends LitElement {
  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
      }
      .tree-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }
      .tree-header h3 {
        margin: 0;
        font-size: 16px;
      }
      .tree-node {
        cursor: pointer;
        padding: 6px 8px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 14px;
        transition: background 0.15s;
      }
      .tree-node:hover {
        background: rgba(0, 0, 0, 0.04);
      }
      .tree-node.selected {
        background: rgba(3, 169, 244, 0.1);
        color: var(--dm-primary);
        font-weight: 500;
      }
      .tree-children {
        padding-left: 20px;
      }
      .toggle {
        width: 16px;
        text-align: center;
        font-size: 10px;
        color: var(--dm-text-secondary);
      }
      .node-name {
        flex: 1;
      }
      .node-actions {
        display: flex;
        gap: 2px;
      }
      .node-actions button {
        padding: 2px 4px;
        font-size: 11px;
      }
      .inline-form {
        display: flex;
        gap: 4px;
        padding: 4px 8px;
        align-items: center;
      }
      .inline-form input {
        padding: 4px 8px;
        font-size: 13px;
        border: 1px solid var(--dm-border);
        border-radius: 4px;
        flex: 1;
      }
    `,
  ];

  @property({ type: Object }) tree: HierarchyTree | null = null;
  @property({ type: Object }) selectedNode: HierarchyNode | null = null;

  @state() private _expandedNodes: Set<string> = new Set();
  @state() private _addingTo: string | null = null;
  @state() private _newName = "";
  @state() private _confirmOpen = false;
  @state() private _pendingDeleteType: string | null = null;
  @state() private _pendingDeleteId: number | null = null;

  private static readonly _STORAGE_KEY = "dm_tree_expanded";

  private _buildingClient = new BuildingClient();
  private _floorClient = new FloorClient();
  private _roomClient = new RoomClient();

  connectedCallback() {
    super.connectedCallback();
    this._restoreExpandedState();
  }

  /** Restore expanded nodes from sessionStorage. */
  private _restoreExpandedState() {
    try {
      const raw = sessionStorage.getItem(DmHierarchyTreeComponent._STORAGE_KEY);
      if (raw) {
        const arr: string[] = JSON.parse(raw);
        if (Array.isArray(arr)) {
          this._expandedNodes = new Set(arr);
        }
      }
    } catch {
      // Ignore corrupt data
    }
  }

  /** Persist expanded nodes to sessionStorage. */
  private _saveExpandedState() {
    try {
      sessionStorage.setItem(
        DmHierarchyTreeComponent._STORAGE_KEY,
        JSON.stringify([...this._expandedNodes])
      );
    } catch {
      // Storage full or unavailable
    }
  }

  render() {
    return html`
      <div class="tree-header">
        <h3>${i18n.t("hierarchy_title")}</h3>
        <button
          class="btn btn-primary"
          style="padding: 4px 10px; font-size: 12px;"
          @click=${() => this._startAdd("building", 0)}
        >
          + ${i18n.t("building")}
        </button>
      </div>

      ${this._addingTo === "building:0"
        ? this._renderInlineAdd("building")
        : nothing}
      ${this.tree?.buildings.map((building) =>
        this._renderBuildingNode(building)
      ) ?? nothing}

      <dm-confirm-dialog
        .open=${this._confirmOpen}
        .message=${i18n.t("confirm_delete")}
        .cascade=${true}
        @dialog-confirm=${this._onConfirmDelete}
        @dialog-cancel=${this._onCancelDelete}
      ></dm-confirm-dialog>
    `;
  }

  private _renderBuildingNode(building: HierarchyNode) {
    const key = `building:${building.id}`;
    const expanded = this._expandedNodes.has(key);
    const selected =
      this.selectedNode?.type === "building" &&
      this.selectedNode?.id === building.id;

    return html`
      <div>
        <div
          class="tree-node ${selected ? "selected" : ""}"
          @click=${() => this._selectNode(building)}
        >
          <span
            class="toggle"
            @click=${(e: Event) => {
              e.stopPropagation();
              this._toggleExpand(key);
            }}
          >
            ${building.children.length > 0 ? (expanded ? "▼" : "▶") : "·"}
          </span>
          <span class="node-name">🏠 ${building.name}</span>
          <span class="badge">${building.deviceCount}</span>
          <span class="node-actions">
            <button
              class="btn-icon"
              title="${i18n.t("add_floor")}"
              @click=${(e: Event) => {
                e.stopPropagation();
                this._startAdd("floor", building.id);
              }}
            >
              +
            </button>
            <button
              class="btn-icon"
              title="${i18n.t("delete_building")}"
              @click=${(e: Event) => {
                e.stopPropagation();
                this._requestDelete("building", building.id);
              }}
            >
              🗑
            </button>
          </span>
        </div>
        ${this._addingTo === `floor:${building.id}`
          ? this._renderInlineAdd("floor")
          : nothing}
        ${expanded
          ? html`<div class="tree-children">
              ${building.children.map((fl) =>
                this._renderFloorNode(fl, building.id)
              )}
            </div>`
          : nothing}
      </div>
    `;
  }

  private _renderFloorNode(floor: HierarchyNode, _buildingId: number) {
    const key = `floor:${floor.id}`;
    const expanded = this._expandedNodes.has(key);
    const selected =
      this.selectedNode?.type === "floor" && this.selectedNode?.id === floor.id;

    return html`
      <div>
        <div
          class="tree-node ${selected ? "selected" : ""}"
          @click=${() => this._selectNode(floor)}
        >
          <span
            class="toggle"
            @click=${(e: Event) => {
              e.stopPropagation();
              this._toggleExpand(key);
            }}
          >
            ${floor.children.length > 0 ? (expanded ? "▼" : "▶") : "·"}
          </span>
          <span class="node-name">🏢 ${floor.name}</span>
          <span class="badge">${floor.deviceCount}</span>
          <span class="node-actions">
            <button
              class="btn-icon"
              title="${i18n.t("add_room")}"
              @click=${(e: Event) => {
                e.stopPropagation();
                this._startAdd("room", floor.id);
              }}
            >
              +
            </button>
            <button
              class="btn-icon"
              title="${i18n.t("delete_floor")}"
              @click=${(e: Event) => {
                e.stopPropagation();
                this._requestDelete("floor", floor.id);
              }}
            >
              🗑
            </button>
          </span>
        </div>
        ${this._addingTo === `room:${floor.id}`
          ? this._renderInlineAdd("room")
          : nothing}
        ${expanded
          ? html`<div class="tree-children">
              ${floor.children.map((room) => this._renderRoomNode(room))}
            </div>`
          : nothing}
      </div>
    `;
  }

  private _renderRoomNode(room: HierarchyNode) {
    const selected =
      this.selectedNode?.type === "room" && this.selectedNode?.id === room.id;

    return html`
      <div
        class="tree-node ${selected ? "selected" : ""}"
        @click=${() => this._selectNode(room)}
      >
        <span class="toggle">·</span>
        <span class="node-name">🚪 ${room.name}</span>
        <span class="badge">${room.deviceCount}</span>
        <span class="node-actions">
          <button
            class="btn-icon"
            title="${i18n.t("delete_room")}"
            @click=${(e: Event) => {
              e.stopPropagation();
              this._requestDelete("room", room.id);
            }}
          >
            🗑
          </button>
        </span>
      </div>
    `;
  }

  private _renderInlineAdd(type: string) {
    return html`
      <div class="inline-form">
        <input
          type="text"
          placeholder="${i18n.t("name")}"
          .value=${this._newName}
          @input=${(e: Event) => {
            this._newName = (e.target as HTMLInputElement).value;
          }}
          @keyup=${(e: KeyboardEvent) => {
            if (e.key === "Enter") this._confirmAdd(type);
            if (e.key === "Escape") this._cancelAdd();
          }}
        />
        <button
          class="btn btn-primary"
          style="padding: 4px 8px; font-size: 12px;"
          @click=${() => this._confirmAdd(type)}
        >
          ✓
        </button>
        <button
          class="btn btn-secondary"
          style="padding: 4px 8px; font-size: 12px;"
          @click=${this._cancelAdd}
        >
          ✕
        </button>
      </div>
    `;
  }

  private _toggleExpand(key: string) {
    const nextSet = new Set(this._expandedNodes);
    if (nextSet.has(key)) nextSet.delete(key);
    else nextSet.add(key);
    this._expandedNodes = nextSet;
    this._saveExpandedState();
  }

  /**
   * Expand all ancestor nodes so that the given node is visible in the tree.
   * Called externally by hierarchy-view when a child is clicked in the detail panel.
   */
  public expandToNode(node: HierarchyNode) {
    if (!this.tree) return;
    const nextSet = new Set(this._expandedNodes);

    for (const building of this.tree.buildings) {
      if (node.type === "building" && node.id === building.id) break;
      for (const floor of building.children) {
        if (node.type === "floor" && node.id === floor.id) {
          nextSet.add(`building:${building.id}`);
          break;
        }
        for (const room of floor.children) {
          if (node.type === "room" && node.id === room.id) {
            nextSet.add(`building:${building.id}`);
            nextSet.add(`floor:${floor.id}`);
            break;
          }
        }
      }
    }

    this._expandedNodes = nextSet;
    this._saveExpandedState();
  }

  private _selectNode(node: HierarchyNode) {
    this.dispatchEvent(
      new CustomEvent("node-selected", {
        detail: { node },
        bubbles: true,
        composed: true,
      })
    );
  }

  private _startAdd(type: string, parentId: number) {
    this._addingTo = `${type}:${parentId}`;
    this._newName = "";
  }

  private _cancelAdd() {
    this._addingTo = null;
    this._newName = "";
  }

  private async _confirmAdd(type: string) {
    if (!this._newName.trim()) return;
    const slug = toSlug(this._newName);
    const parentId = parseInt(this._addingTo?.split(":")[1] ?? "0", 10);
    try {
      if (type === "building") {
        await this._buildingClient.create({ name: this._newName, slug });
      } else if (type === "floor") {
        await this._floorClient.create({
          name: this._newName,
          slug,
          buildingId: parentId,
        });
      } else if (type === "room") {
        await this._roomClient.create({
          name: this._newName,
          slug,
          floorId: parentId,
        });
      }
      this._cancelAdd();
      this.dispatchEvent(
        new CustomEvent("tree-changed", { bubbles: true, composed: true })
      );
    } catch (err) {
      console.error(`Failed to create ${type}:`, err);
    }
  }

  private _requestDelete(type: string, id: number) {
    this._pendingDeleteType = type;
    this._pendingDeleteId = id;
    this._confirmOpen = true;
  }

  private async _onConfirmDelete() {
    this._confirmOpen = false;
    const type = this._pendingDeleteType;
    const id = this._pendingDeleteId;
    this._pendingDeleteType = null;
    this._pendingDeleteId = null;
    if (!type || id == null) return;
    try {
      if (type === "building") await this._buildingClient.remove(id);
      else if (type === "floor") await this._floorClient.remove(id);
      else if (type === "room") await this._roomClient.remove(id);
      this.dispatchEvent(
        new CustomEvent("tree-changed", { bubbles: true, composed: true })
      );
    } catch (err) {
      console.error(`Failed to delete ${type}:`, err);
    }
  }

  private _onCancelDelete() {
    this._confirmOpen = false;
    this._pendingDeleteType = null;
    this._pendingDeleteId = null;
  }
}
