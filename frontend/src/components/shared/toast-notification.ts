/**
 * Toast notification component.
 */
import { LitElement, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import sharedStyles from "../../styles/shared.css?lit";
import toastNotificationStyles from "./toast-notification.css?lit";

@customElement("dm-toast")
export class DmToast extends LitElement {
  static styles = [sharedStyles, toastNotificationStyles];

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
