/**
 * API client for DmDeviceFirmware CRUD operations.
 */
import type { DmDeviceFirmware } from "../types/device-firmware";
import { CrudClient } from "./crud-client";

export class DeviceFirmwareClient extends CrudClient<DmDeviceFirmware> {
  constructor() {
    super("/device-firmwares");
  }
}
