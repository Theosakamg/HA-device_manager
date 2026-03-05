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
import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { unsafeHTML } from "lit/directives/unsafe-html.js";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { sharedStyles } from "../../styles/shared-styles";
import type { DocContent } from "../../utils/frontmatter";

@customElement("dm-doc-block")
export class DmDocBlock extends LitElement {
  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
      }
      .wrapper {
        margin: 0 0 20px 0;
        background: var(--secondary-background-color, #f5f5f5);
        border-left: 3px solid var(--primary-color, #03a9f4);
        border-radius: 4px;
        overflow: hidden;
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 16px;
        cursor: pointer;
        user-select: none;
      }
      .header:hover {
        background: rgba(0, 0, 0, 0.03);
      }
      .summary {
        color: var(--secondary-text-color, #666);
        font-size: 13px;
        line-height: 1.4;
        margin: 0;
        flex: 1;
      }
      .toggle {
        background: none;
        border: none;
        cursor: pointer;
        font-size: 16px;
        padding: 0 0 0 12px;
        color: var(--secondary-text-color, #888);
        transition: transform 0.2s;
        line-height: 1;
      }
      .toggle.expanded {
        transform: rotate(180deg);
      }
      .body {
        color: var(--secondary-text-color, #666);
        font-size: 13px;
        line-height: 1.6;
        padding: 0 16px 12px 16px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
      }
      .body p {
        margin: 8px 0;
      }
      .body p:first-child {
        margin-top: 8px;
      }
      .body p:last-child {
        margin-bottom: 0;
      }
      .body strong {
        color: var(--primary-text-color, #333);
      }
      .body em {
        font-style: italic;
      }
      .body code {
        background: var(--divider-color, #e0e0e0);
        padding: 1px 5px;
        border-radius: 3px;
        font-size: 12px;
        font-family: monospace;
      }
      .body ul,
      .body ol {
        margin: 6px 0;
        padding-left: 20px;
      }
      .body li {
        margin-bottom: 3px;
      }
      .body table {
        border-collapse: collapse;
        width: 100%;
        margin: 8px 0;
        font-size: 12px;
      }
      .body th,
      .body td {
        border: 1px solid var(--divider-color, #e0e0e0);
        padding: 5px 10px;
        text-align: left;
      }
      .body th {
        background: rgba(0, 0, 0, 0.04);
        font-weight: 600;
      }
      .body blockquote {
        margin: 8px 0;
        padding: 6px 12px;
        border-left: 2px solid var(--primary-color, #03a9f4);
        background: rgba(3, 169, 244, 0.06);
        border-radius: 0 4px 4px 0;
        font-style: italic;
      }
      .body blockquote p {
        margin: 0;
      }
    `,
  ];

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
