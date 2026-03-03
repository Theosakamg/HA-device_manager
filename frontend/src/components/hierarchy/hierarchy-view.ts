/**
 * Hierarchy view - combined tree + detail panel.
 */
import { LitElement, html, css } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";
import type { HierarchyNode, HierarchyTree } from "../../types/device";
import { HierarchyClient } from "../../api/hierarchy-client";
import type { DmHierarchyTreeComponent } from "./hierarchy-tree";
import "./hierarchy-tree";
import "./node-detail";

@localized
@customElement("dm-hierarchy-view")
export class DmHierarchyView extends LitElement {
  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        height: 100%;
      }
      .container {
        display: flex;
        gap: 16px;
        height: 100%;
        min-height: calc(100vh - 100px);
      }
      .tree-panel {
        width: 30%;
        min-width: 250px;
        overflow-y: auto;
        background: var(--dm-card-bg);
        border-radius: var(--dm-radius);
        box-shadow: var(--dm-shadow);
        padding: 16px;
      }
      .detail-panel {
        flex: 1;
        overflow-y: auto;
        background: var(--dm-card-bg);
        border-radius: var(--dm-radius);
        box-shadow: var(--dm-shadow);
        padding: 16px;
      }
      @media (max-width: 768px) {
        .container {
          flex-direction: column;
        }
        .tree-panel {
          width: 100%;
          min-height: auto;
        }
      }
    `,
  ];

  @state() private _tree: HierarchyTree | null = null;
  @state() private _selectedNode: HierarchyNode | null = null;
  @state() private _loading = true;

  private _client = new HierarchyClient();

  async connectedCallback() {
    super.connectedCallback();
    await this._loadTree();
  }

  async _loadTree() {
    this._loading = true;
    try {
      this._tree = await this._client.getTree();
      // Auto-select first item if nothing is selected
      if (!this._selectedNode && this._tree?.buildings?.length) {
        this._selectedNode = this._tree.buildings[0];
      }
    } catch (err) {
      console.error("Failed to load hierarchy:", err);
    }
    this._loading = false;
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
                @data-changed=${this._loadTree}
                @node-selected=${this._onNodeSelected}
                @expand-to-node=${this._onExpandToNode}
              ></dm-node-detail>`
            : html`<div class="empty-state">
                <p>${i18n.t("hierarchy_title")}</p>
                <p style="font-size: 14px; color: var(--dm-text-secondary);">
                  ${i18n.t("no_homes")}
                </p>
              </div>`}
        </div>
      </div>
    `;
  }

  private _onNodeSelected(e: CustomEvent) {
    this._selectedNode = e.detail.node;
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
