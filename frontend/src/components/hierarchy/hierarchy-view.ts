/**
 * Hierarchy view - combined tree + detail panel.
 */
import { LitElement, html } from "lit";
import { customElement, state } from "lit/decorators.js";
import sharedStyles from "../../styles/shared.css?lit";
import hierarchyViewStyles from "./hierarchy-view.css?lit";
import { i18n, localized } from "../../i18n";
import type { HierarchyNode, HierarchyTree } from "../../types/device";
import { HierarchyClient } from "../../api/hierarchy-client";
import type { DmHierarchyTreeComponent } from "./hierarchy-tree";
import "./hierarchy-tree";
import "./node-detail";

@localized
@customElement("dm-hierarchy-view")
export class DmHierarchyView extends LitElement {
  static styles = [sharedStyles, hierarchyViewStyles];

  @state() private _tree: HierarchyTree | null = null;
  @state() private _selectedNode: HierarchyNode | null = null;
  @state() private _loading = true;

  private _client = new HierarchyClient();
  private static readonly _SELECTION_KEY = "dm_hierarchy_selected";

  private _saveSelection(node: HierarchyNode | null) {
    try {
      if (node) {
        sessionStorage.setItem(
          DmHierarchyView._SELECTION_KEY,
          JSON.stringify({ id: node.id, type: node.type })
        );
      } else {
        sessionStorage.removeItem(DmHierarchyView._SELECTION_KEY);
      }
    } catch {
      // Ignore
    }
  }

  private _restoreSelection(): { id: number; type: string } | null {
    try {
      const raw = sessionStorage.getItem(DmHierarchyView._SELECTION_KEY);
      if (raw) return JSON.parse(raw);
    } catch {
      // Ignore corrupt data
    }
    return null;
  }

  async connectedCallback() {
    super.connectedCallback();
    const saved = this._restoreSelection();
    if (saved) {
      this._selectedNode = { id: saved.id, type: saved.type } as HierarchyNode;
    }
    await this._loadTree();
  }

  async _loadTree() {
    this._loading = true;
    try {
      this._tree = await this._client.getTree();
      if (!this._selectedNode && this._tree?.buildings?.length) {
        // Nothing selected yet: auto-select first building
        this._selectedNode = this._tree.buildings[0];
      } else if (this._selectedNode) {
        // Refresh the selected node reference from the new tree so the detail
        // panel reflects the latest saved values.
        const refreshed = this._findNodeByIdAndType(
          this._tree,
          this._selectedNode.id,
          this._selectedNode.type
        );
        if (refreshed) this._selectedNode = refreshed;
      }
    } catch (err) {
      console.error("Failed to load hierarchy:", err);
    }
    this._loading = false;
  }

  /** Depth-first search for a node by id and type across the entire hierarchy tree.
   * Matching on both fields is required because IDs are only unique within a type
   * (a building and a floor can share the same numeric id).
   */
  private _findNodeByIdAndType(
    tree: HierarchyTree | null,
    id: number,
    type: string
  ): HierarchyNode | null {
    if (!tree) return null;
    const stack: HierarchyNode[] = [...(tree.buildings ?? [])];
    while (stack.length) {
      const node = stack.pop()!;
      if (node.id === id && node.type === type) return node;
      if (node.children?.length) stack.push(...node.children);
    }
    return null;
  }

  render() {
    if (this._loading) {
      return html`<div class="loading">${i18n.t("loading")}</div>`;
    }

    return html`
      <div class="container">
        <div class="tree-panel">
          <dm-hierarchy-tree
            .tree=${this._tree}
            .selectedNode=${this._selectedNode}
            @node-selected=${this._onNodeSelected}
            @tree-changed=${this._loadTree}
          ></dm-hierarchy-tree>
        </div>
        <div class="detail-panel">
          ${this._selectedNode
            ? html`<dm-node-detail
                .node=${this._selectedNode}
                .tree=${this._tree}
                @data-changed=${this._loadTree}
                @node-selected=${this._onNodeSelected}
                @expand-to-node=${this._onExpandToNode}
              ></dm-node-detail>`
            : html`<div class="empty-state">
                <p>${i18n.t("hierarchy_title")}</p>
                <p style="font-size: 14px; color: var(--dm-text-secondary);">
                  ${i18n.t("no_buildings")}
                </p>
              </div>`}
        </div>
      </div>
    `;
  }

  private _onNodeSelected(e: CustomEvent) {
    this._selectedNode = e.detail.node;
    this._saveSelection(this._selectedNode);
  }

  private _onExpandToNode(e: CustomEvent) {
    const node = e.detail.node as HierarchyNode;
    const treeEl = this.shadowRoot?.querySelector(
      "dm-hierarchy-tree"
    ) as DmHierarchyTreeComponent | null;
    if (treeEl) {
      treeEl.expandToNode(node);
    }
  }
}
