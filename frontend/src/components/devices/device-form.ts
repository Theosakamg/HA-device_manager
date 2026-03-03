/**
 * Device form component - modal form with FK select dropdowns.
 */
import { LitElement, html, css } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";
import { getSettings } from "../../api/settings-client";
import type { DmDevice } from "../../types/device";
import type { DmRoom } from "../../types/room";
import type { DmDeviceModel } from "../../types/device-model";
import type { DmDeviceFirmware } from "../../types/device-firmware";
import type { DmDeviceFunction } from "../../types/device-function";
import { RoomClient } from "../../api/room-client";

import { DeviceModelClient } from "../../api/device-model-client";
import { DeviceFirmwareClient } from "../../api/device-firmware-client";
import { DeviceFunctionClient } from "../../api/device-function-client";
import { DeviceClient } from "../../api/device-client";

@localized
@customElement("dm-device-form")
export class DmDeviceForm extends LitElement {
  static styles = [
    sharedStyles,
    css`
      .form-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      .form-full {
        grid-column: 1 / -1;
      }
      @media (max-width: 600px) {
        .form-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ];

  @property({ type: Object }) device: DmDevice | null = null;

  @state() private _rooms: DmRoom[] = [];
  @state() private _models: DmDeviceModel[] = [];
  @state() private _firmwares: DmDeviceFirmware[] = [];
  @state() private _functions: DmDeviceFunction[] = [];
  @state() private _allDevices: DmDevice[] = [];
  @state() private _loading = true;
  @state() private _form: Record<string, unknown> = {};

  private _roomClient = new RoomClient();
  private _modelClient = new DeviceModelClient();
  private _firmwareClient = new DeviceFirmwareClient();
  private _functionClient = new DeviceFunctionClient();
  private _deviceClient = new DeviceClient();

  async connectedCallback() {
    super.connectedCallback();
    await this._loadRefs();
    this._initForm();
  }

  private async _loadRefs() {
    this._loading = true;
    try {
      const [rooms, models, firmwares, functions, devices] = await Promise.all([
        this._roomClient.getAll(),
        this._modelClient.getAll(),
        this._firmwareClient.getAll(),
        this._functionClient.getAll(),
        this._deviceClient.getAll(),
      ]);
      this._rooms = rooms;
      this._models = models;
      this._firmwares = firmwares;
      this._functions = functions;
      this._allDevices = devices;
    } catch (err) {
      console.error("Failed to load refs:", err);
    }
    this._loading = false;
  }

  private _initForm() {
    if (this.device) {
      this._form = {
        mac: this.device.mac ?? "",
        ip: this.device.ip ?? "",
        positionName: this.device.positionName ?? "",
        positionSlug: this.device.positionSlug ?? "",
        mode: this.device.mode ?? "",
        interlock: this.device.interlock ?? "",
        haDeviceClass: this.device.haDeviceClass ?? "",
        extra: this.device.extra ?? "",
        enabled: this.device.enabled ?? true,
        roomId: this.device.roomId ?? "",
        modelId: this.device.modelId ?? "",
        firmwareId: this.device.firmwareId ?? "",
        functionId: this.device.functionId ?? "",
        targetId: this.device.targetId ?? "",
      };
    } else {
      this._form = {
        mac: "",
        ip: "",
        positionName: "",
        positionSlug: "",
        mode: "",
        interlock: "",
        haDeviceClass: "",
        extra: "",
        enabled: true,
        roomId: "",
        modelId: "",
        firmwareId: "",
        functionId: "",
        targetId: "",
      };
    }
  }

  private _updateField(key: string, value: unknown) {
    this._form = { ...this._form, [key]: value };
  }

  render() {
    if (this._loading)
      return html`<div class="loading">${i18n.t("loading")}</div>`;

    const isEdit = this.device !== null;
    return html`
      <div class="modal-overlay" @click=${this._cancel}>
        <div
          class="modal"
          @click=${(e: Event) => e.stopPropagation()}
          style="max-width: 700px;"
        >
          <div class="modal-header">
            <h2>${isEdit ? i18n.t("edit_device") : i18n.t("add_device")}</h2>
            <button class="btn-icon" @click=${this._cancel}>✕</button>
          </div>

          <div class="form-grid">
            <div class="form-group">
              <label>${i18n.t("device_mac")}</label>
              <input
                type="text"
                .value=${String(this._form.mac ?? "")}
                placeholder="AA:BB:CC:DD:EE:FF"
                @input=${(e: Event) =>
                  this._updateField(
                    "mac",
                    (e.target as HTMLInputElement).value
                  )}
              />
            </div>
            <div class="form-group">
              <label>${i18n.t("device_ip")}</label>
              <input
                type="text"
                .value=${String(this._form.ip ?? "")}
                placeholder="${getSettings().ip_prefix}.x"
                @input=${(e: Event) =>
                  this._updateField("ip", (e.target as HTMLInputElement).value)}
              />
            </div>
            <div class="form-group">
              <label>${i18n.t("device_position_name")}</label>
              <input
                type="text"
                .value=${String(this._form.positionName ?? "")}
                @input=${(e: Event) =>
                  this._updateField(
                    "positionName",
                    (e.target as HTMLInputElement).value
                  )}
              />
            </div>
            <div class="form-group">
              <label>${i18n.t("device_position_slug")}</label>
              <input
                type="text"
                .value=${String(this._form.positionSlug ?? "")}
                @input=${(e: Event) =>
                  this._updateField(
                    "positionSlug",
                    (e.target as HTMLInputElement).value
                  )}
              />
            </div>
            <div class="form-group">
              <label>${i18n.t("device_mode")}</label>
              <input
                type="text"
                .value=${String(this._form.mode ?? "")}
                @input=${(e: Event) =>
                  this._updateField(
                    "mode",
                    (e.target as HTMLInputElement).value
                  )}
              />
            </div>
            <div class="form-group">
              <label>${i18n.t("device_interlock")}</label>
              <input
                type="text"
                .value=${String(this._form.interlock ?? "")}
                @input=${(e: Event) =>
                  this._updateField(
                    "interlock",
                    (e.target as HTMLInputElement).value
                  )}
              />
            </div>
            <div class="form-group">
              <label>${i18n.t("device_ha_class")}</label>
              <input
                type="text"
                .value=${String(this._form.haDeviceClass ?? "")}
                @input=${(e: Event) =>
                  this._updateField(
                    "haDeviceClass",
                    (e.target as HTMLInputElement).value
                  )}
              />
            </div>
            <div class="form-group">
              <label>${i18n.t("device_enabled")}</label>
              <select
                @change=${(e: Event) =>
                  this._updateField(
                    "enabled",
                    (e.target as HTMLSelectElement).value === "true"
                  )}
              >
                <option value="true" ?selected=${Boolean(this._form.enabled)}>
                  ${i18n.t("enabled")}
                </option>
                <option value="false" ?selected=${!this._form.enabled}>
                  ${i18n.t("disabled")}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>${i18n.t("device_room")}</label>
              <select
                .value=${String(this._form.roomId ?? "")}
                @change=${(e: Event) =>
                  this._updateField(
                    "roomId",
                    parseInt((e.target as HTMLSelectElement).value) || null
                  )}
              >
                <option value="">${i18n.t("select_room")}</option>
                ${this._rooms.map(
                  (r) =>
                    html`<option
                      value=${r.id}
                      ?selected=${this._form.roomId === r.id}
                    >
                      ${r.name}
                    </option>`
                )}
              </select>
            </div>
            <div class="form-group">
              <label>${i18n.t("device_model")}</label>
              <select
                .value=${String(this._form.modelId ?? "")}
                @change=${(e: Event) =>
                  this._updateField(
                    "modelId",
                    parseInt((e.target as HTMLSelectElement).value) || null
                  )}
              >
                <option value="">${i18n.t("select_model")}</option>
                ${this._models.map(
                  (m) =>
                    html`<option
                      value=${m.id}
                      ?selected=${this._form.modelId === m.id}
                    >
                      ${m.name}
                    </option>`
                )}
              </select>
            </div>
            <div class="form-group">
              <label>${i18n.t("device_firmware")}</label>
              <select
                .value=${String(this._form.firmwareId ?? "")}
                @change=${(e: Event) =>
                  this._updateField(
                    "firmwareId",
                    parseInt((e.target as HTMLSelectElement).value) || null
                  )}
              >
                <option value="">${i18n.t("select_firmware")}</option>
                ${this._firmwares.map(
                  (f) =>
                    html`<option
                      value=${f.id}
                      ?selected=${this._form.firmwareId === f.id}
                    >
                      ${f.name}
                    </option>`
                )}
              </select>
            </div>
            <div class="form-group">
              <label>${i18n.t("device_function")}</label>
              <select
                .value=${String(this._form.functionId ?? "")}
                @change=${(e: Event) =>
                  this._updateField(
                    "functionId",
                    parseInt((e.target as HTMLSelectElement).value) || null
                  )}
              >
                <option value="">${i18n.t("select_function")}</option>
                ${this._functions.map(
                  (fn) =>
                    html`<option
                      value=${fn.id}
                      ?selected=${this._form.functionId === fn.id}
                    >
                      ${fn.name}
                    </option>`
                )}
              </select>
            </div>
            <div class="form-group">
              <label>${i18n.t("device_target")}</label>
              <select
                .value=${String(this._form.targetId ?? "")}
                @change=${(e: Event) =>
                  this._updateField(
                    "targetId",
                    parseInt((e.target as HTMLSelectElement).value) || null
                  )}
              >
                <option value="">${i18n.t("select_target")}</option>
                ${this._allDevices
                  .filter((d) => d.id !== this.device?.id)
                  .map(
                    (d) =>
                      html`<option
                        value=${d.id}
                        ?selected=${this._form.targetId === d.id}
                      >
                        ${d.mac} - ${d.positionName}
                      </option>`
                  )}
              </select>
            </div>
            <div class="form-group form-full">
              <label>${i18n.t("device_extra")}</label>
              <textarea
                rows="3"
                .value=${String(this._form.extra ?? "")}
                @input=${(e: Event) =>
                  this._updateField(
                    "extra",
                    (e.target as HTMLTextAreaElement).value
                  )}
              ></textarea>
            </div>
          </div>

          <div class="modal-actions">
            <button class="btn btn-secondary" @click=${this._cancel}>
              ${i18n.t("cancel")}
            </button>
            <button class="btn btn-primary" @click=${this._save}>
              ${i18n.t("save")}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  private _cancel() {
    this.dispatchEvent(
      new CustomEvent("form-cancel", { bubbles: true, composed: true })
    );
  }

  /** Normalize empty strings to null for nullable DB columns. */
  private _normalizeNullables(
    data: Record<string, unknown>
  ): Record<string, unknown> {
    const nullableFields = [
      "ip",
      "targetId",
      "interlock",
      "haDeviceClass",
      "extra",
      "mode",
    ];
    const result = { ...data };
    for (const key of nullableFields) {
      if (
        typeof result[key] === "string" &&
        (result[key] as string).trim() === ""
      ) {
        result[key] = null;
      }
    }
    return result;
  }

  private _save() {
    const detail = {
      isEdit: this.device !== null,
      id: this.device?.id,
      data: this._normalizeNullables(this._form),
    };
    this.dispatchEvent(
      new CustomEvent("form-save", { detail, bubbles: true, composed: true })
    );
  }
}
