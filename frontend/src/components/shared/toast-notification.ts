/**
 * Toast notification component.
 */
import { LitElement, html, css } from "lit";
import { customElement, property } from "lit/decorators.js";

@customElement("dm-toast")
export class DmToast extends LitElement {
  static styles = css`
    :host {
      position: fixed;
      bottom: 20px;
      right: 20px;
      z-index: 2000;
    }
    .toast {
      padding: 12px 24px;
      border-radius: 4px;
      color: white;
      font-size: 14px;
      animation: slideIn 0.3s ease-out;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .success {
      background: #4caf50;
    }
    .error {
      background: #f44336;
    }
    .info {
      background: #03a9f4;
    }
    @keyframes slideIn {
      from {
        transform: translateX(100%);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
  `;

  @property({ type: String }) message = "";
  @property({ type: String }) type: "success" | "error" | "info" = "info";
  @property({ type: Boolean }) visible = false;

  private _timeout?: ReturnType<typeof setTimeout>;

  disconnectedCallback() {
    super.disconnectedCallback();
    if (this._timeout) {
      clearTimeout(this._timeout);
      this._timeout = undefined;
    }
  }

  show(
    message: string,
    type: "success" | "error" | "info" = "info",
    duration = 3000
  ) {
    this.message = message;
    this.type = type;
    this.visible = true;
    if (this._timeout) clearTimeout(this._timeout);
    this._timeout = setTimeout(() => {
      this.visible = false;
    }, duration);
  }

  render() {
    if (!this.visible) return html``;
    return html`<div class="toast ${this.type}">${this.message}</div>`;
  }
}
