/**
 * API client for DmDeviceFunction CRUD operations.
 */
import type { DmDeviceFunction } from "../types/device-function";
import { CrudClient } from "./crud-client";

export class DeviceFunctionClient extends CrudClient<DmDeviceFunction> {
  constructor() {
    super("/device-functions");
  }
}
