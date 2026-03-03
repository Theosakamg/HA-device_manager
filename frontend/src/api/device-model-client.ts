/**
 * API client for DmDeviceModel CRUD operations.
 */
import type { DmDeviceModel } from "../types/device-model";
import { CrudClient } from "./crud-client";

export class DeviceModelClient extends CrudClient<DmDeviceModel> {
  constructor() {
    super("/device-models");
  }
}
