/**
 * Confirmation dialog component.
 */
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";

@localized
@customElement("dm-confirm-dialog")
export class DmConfirmDialog extends LitElement {
  static styles = [
    sharedStyles,
    css`
      .message {
        margin: 16px 0;
        font-size: 16px;
        line-height: 1.5;
      }
    `,
  ];

  @property({ type: Boolean }) open = false;
  @property({ type: String }) message = "";
  @property({ type: Boolean }) cascade = false;

  render() {
    if (!this.open) return html``;
    return html`
      <div class="modal-overlay" @click=${this._cancel}>
        <div
          class="modal"
          @click=${(e: Event) => e.stopPropagation()}
          style="max-width: 400px;"
        >
          <div class="modal-header">
            <h2>${i18n.t("confirm")}</h2>
          </div>
          <div class="message">
            ${this.message || i18n.t("confirm_delete")}
            ${this.cascade
              ? html`<br /><strong>${i18n.t("confirm_delete_cascade")}</strong>`
              : ""}
          </div>
          <div class="modal-actions">
            <button class="btn btn-secondary" @click=${this._cancel}>
              ${i18n.t("cancel")}
            </button>
            <button class="btn btn-danger" @click=${this._confirm}>
              ${i18n.t("delete")}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  private _cancel() {
    this.dispatchEvent(
      new CustomEvent("dialog-cancel", { bubbles: true, composed: true })
    );
  }

  private _confirm() {
    this.dispatchEvent(
      new CustomEvent("dialog-confirm", { bubbles: true, composed: true })
    );
  }
}
