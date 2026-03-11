/**
 * Reusable collapsible documentation block.
 *
 * Displays a DocContent (from doc-registry) as a collapsible card:
 * - collapsed → shows `summary` (inline markdown)
 * - expanded  → shows `body` (full markdown)
 *
 * Usage:
 *   <dm-doc-block .doc=${getDoc("settings.overview")}></dm-doc-block>
 */
import { LitElement, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { marked } from "marked";
import DOMPurify from "dompurify";
import sharedStyles from "../../styles/shared.css?lit";
import docBlockStyles from "./doc-block.css?lit";
import type { DocContent } from "../../utils/frontmatter";

@customElement("dm-doc-block")
export class DmDocBlock extends LitElement {
  static styles = [sharedStyles, docBlockStyles];

  @property({ attribute: false }) doc?: DocContent;

  /** Optional storage key to persist the collapsed state across reloads. */
  @property({ type: String }) storageKey = "";

  @state() private _expanded = false;

  connectedCallback() {
    super.connectedCallback();
    const key = this._resolvedStorageKey;
    this._expanded = key ? localStorage.getItem(key) === "expanded" : false;
  }

  private get _resolvedStorageKey(): string {
    return this.storageKey ? `dm-doc-expanded-${this.storageKey}` : "";
  }

  private _toggle() {
    this._expanded = !this._expanded;
    const key = this._resolvedStorageKey;
    if (key) {
      localStorage.setItem(key, this._expanded ? "expanded" : "collapsed");
    }
  }

  render() {
    if (!this.doc) return nothing;

    return html`
      <div class="wrapper">
        <div class="header" @click=${this._toggle}>
          <span class="summary">
            ${unsafeHTML(
              DOMPurify.sanitize(marked.parseInline(this.doc.summary) as string)
            )}
          </span>
          <span class="toggle ${this._expanded ? "expanded" : ""}">▼</span>
        </div>
        ${this._expanded
          ? html`<div class="body">
              ${unsafeHTML(
                DOMPurify.sanitize(marked.parse(this.doc.body) as string)
              )}
            </div>`
          : nothing}
      </div>
    `;
  }
}
