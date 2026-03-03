/**
 * Generic CRUD tab — replaces the duplicated model/firmware/function tabs.
 *
 * Usage:
 *   <dm-crud-tab .client=${myClient} .config=${myConfig}></dm-crud-tab>
 */
import { LitElement, html } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import type { CrudClient } from "../../api/crud-client";
import type { CrudConfig } from "../shared/crud-table";
import "../shared/crud-table";

@customElement("dm-crud-tab")
export class DmCrudTab extends LitElement {
  static styles = [sharedStyles];

  @property({ attribute: false }) client!: CrudClient<Record<string, unknown>>;
  @property({ attribute: false }) config!: CrudConfig;

  @state() private _items: Record<string, unknown>[] = [];
  @state() private _loading = true;

  async connectedCallback() {
    super.connectedCallback();
    await this._load();
  }

  private async _load() {
    this._loading = true;
    try {
      this._items = (await this.client.getAll()) as Record<string, unknown>[];
    } catch (err) {
      console.error(
        `Failed to load ${this.config?.entityName ?? "items"}:`,
        err
      );
    }
    this._loading = false;
  }

  render() {
    return html`
      <dm-crud-table
        .items=${this._items}
        .config=${this.config}
        .loading=${this._loading}
        @crud-save=${this._onSave}
        @crud-delete=${this._onDelete}
      ></dm-crud-table>
    `;
  }

  private async _onSave(e: CustomEvent) {
    const { isEdit, id, data } = e.detail;
    try {
      if (isEdit) {
        await this.client.update(id, data);
      } else {
        await this.client.create(data);
      }
      await this._load();
    } catch (err) {
      console.error(
        `Failed to save ${this.config?.entityName ?? "item"}:`,
        err
      );
    }
  }

  private async _onDelete(e: CustomEvent) {
    try {
      await this.client.remove(e.detail.id);
      await this._load();
    } catch (err) {
      console.error(
        `Failed to delete ${this.config?.entityName ?? "item"}:`,
        err
      );
    }
  }
}
