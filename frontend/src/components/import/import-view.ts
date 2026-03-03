/**
 * Import view - CSV file upload and processing.
 */
import { LitElement, html, css, nothing } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";
import { ImportClient } from "../../api/import-client";
import type { ImportResult } from "../../types/device";

@localized
@customElement("dm-import-view")
export class DmImportView extends LitElement {
  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        max-width: 800px;
        margin: 0 auto;
      }
      .upload-zone {
        border: 2px dashed var(--dm-border);
        border-radius: 8px;
        padding: 40px;
        text-align: center;
        cursor: pointer;
        transition: border-color 0.2s;
        margin-bottom: 24px;
      }
      .upload-zone:hover {
        border-color: var(--dm-primary);
      }
      .upload-zone.dragging {
        border-color: var(--dm-primary);
        background: rgba(3, 169, 244, 0.05);
      }
      .file-info {
        margin: 16px 0;
        padding: 12px;
        background: #f5f5f5;
        border-radius: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .result-card {
        margin-top: 24px;
      }
      .log-status {
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 500;
      }
      .log-status-created {
        background: #e8f5e9;
        color: #2e7d32;
      }
      .log-status-updated {
        background: #e3f2fd;
        color: #1565c0;
      }
      .log-status-skipped {
        background: #fff3e0;
        color: #ef6c00;
      }
      .log-status-error {
        background: #fce4ec;
        color: #c62828;
      }
      .error-row-num {
        font-weight: bold;
        margin-right: 8px;
        color: #c62828;
      }
    `,
  ];

  @state() private _file: File | null = null;
  @state() private _dragging = false;
  @state() private _processing = false;
  @state() private _result: ImportResult | null = null;
  @state() private _showErrors = false;

  private _client = new ImportClient();

  render() {
    return html`
      <h2>${i18n.t("import_csv")}</h2>

      ${!this._result
        ? html`
            <div
              class="upload-zone ${this._dragging ? "dragging" : ""}"
              role="button"
              tabindex="0"
              aria-label="${i18n.t("import_file")}"
              @click=${this._openFilePicker}
              @keydown=${this._onKeyDown}
              @dragover=${this._onDragOver}
              @dragleave=${this._onDragLeave}
              @drop=${this._onDrop}
            >
              <p style="font-size: 36px; margin: 0;">📁</p>
              <p>${i18n.t("import_file")}</p>
              <p style="font-size: 12px; color: var(--dm-text-secondary);">
                CSV (UTF-8 or Latin-1)
              </p>
            </div>

            ${this._file
              ? html`
                  <div class="file-info">
                    <span
                      >📄 ${this._file.name}
                      (${(this._file.size / 1024).toFixed(1)} KB)</span
                    >
                    <button
                      class="btn-icon"
                      @click=${() => {
                        this._file = null;
                      }}
                    >
                      ✕
                    </button>
                  </div>
                  <button
                    class="btn btn-primary"
                    ?disabled=${this._processing}
                    @click=${this._startImport}
                  >
                    ${this._processing
                      ? i18n.t("import_processing")
                      : i18n.t("import_start")}
                  </button>
                `
              : nothing}
          `
        : this._renderResult()}
    `;
  }

  private _renderResult() {
    const r = this._result!;
    return html`
      <div class="result-card">
        <h3>✅ ${i18n.t("import_done")}</h3>

        <div class="stats">
          <div class="stat-box">
            <div class="stat-value">${r.total}</div>
            <div class="stat-label">${i18n.t("import_total")}</div>
          </div>
          <div class="stat-box created">
            <div class="stat-value">${r.created}</div>
            <div class="stat-label">${i18n.t("import_created")}</div>
          </div>
          <div class="stat-box updated">
            <div class="stat-value">${r.updated}</div>
            <div class="stat-label">${i18n.t("import_updated")}</div>
          </div>
          <div class="stat-box skipped">
            <div class="stat-value">${r.skipped}</div>
            <div class="stat-label">${i18n.t("import_skipped")}</div>
          </div>
          ${r.errors && r.errors.length > 0
            ? html`
                <div
                  class="stat-box errors"
                  @click=${() => {
                    this._showErrors = !this._showErrors;
                  }}
                >
                  <div class="stat-value">${r.errors.length}</div>
                  <div class="stat-label">${i18n.t("import_errors")} ▼</div>
                </div>
              `
            : nothing}
        </div>

        ${r.errors && r.errors.length > 0
          ? html`
              <div class="error-panel">
                <div
                  class="error-panel-header"
                  @click=${() => {
                    this._showErrors = !this._showErrors;
                  }}
                >
                  <span
                    >⚠️ ${i18n.t("import_errors")} (${r.errors.length})</span
                  >
                  <span>${this._showErrors ? "▲" : "▼"}</span>
                </div>
                ${this._showErrors
                  ? html`
                      <div class="error-panel-body">
                        <ul class="error-list">
                          ${r.errors.map(
                            (err: string) => html`<li>${err}</li>`
                          )}
                        </ul>
                      </div>
                    `
                  : nothing}
              </div>
            `
          : nothing}
        ${r.logs && r.logs.length > 0
          ? html`
              <div class="log-table">
                <table>
                  <thead>
                    <tr>
                      <th>Row</th>
                      <th>Status</th>
                      <th>Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    ${r.logs.map(
                      (entry: {
                        row: number;
                        status: string;
                        message: string;
                      }) => html`
                        <tr>
                          <td>${entry.row}</td>
                          <td>
                            <span class="log-status log-status-${entry.status}"
                              >${entry.status}</span
                            >
                          </td>
                          <td>${entry.message}</td>
                        </tr>
                      `
                    )}
                  </tbody>
                </table>
              </div>
            `
          : nothing}

        <div style="margin-top: 16px;">
          <button class="btn btn-secondary" @click=${this._reset}>
            ${i18n.t("import_csv")}
          </button>
        </div>
      </div>
    `;
  }

  private _openFilePicker() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".csv";
    input.onchange = () => {
      if (input.files?.[0]) {
        this._file = input.files[0];
        this._result = null;
      }
    };
    input.click();
  }

  private _onKeyDown(e: KeyboardEvent) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      this._openFilePicker();
    }
  }

  private _onDragOver(e: DragEvent) {
    e.preventDefault();
    this._dragging = true;
  }

  private _onDragLeave() {
    this._dragging = false;
  }

  private _onDrop(e: DragEvent) {
    e.preventDefault();
    this._dragging = false;
    const file = e.dataTransfer?.files?.[0];
    if (
      file &&
      (file.name.toLowerCase().endsWith(".csv") || file.type === "text/csv")
    ) {
      this._file = file;
      this._result = null;
    }
  }

  private async _startImport() {
    if (!this._file) return;
    this._processing = true;
    try {
      this._result = await this._client.importCSV(this._file);
    } catch (err) {
      console.error("Import failed:", err);
      this._result = {
        total: 0,
        created: 0,
        updated: 0,
        skipped: 0,
        errors: [String(err)],
        logs: [],
      };
      this._showErrors = true;
    }
    this._processing = false;
  }

  private _reset() {
    this._file = null;
    this._result = null;
    this._showErrors = false;
  }
}
