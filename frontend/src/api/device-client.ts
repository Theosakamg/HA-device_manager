/**
 * API client for DmDevice CRUD operations.
 */
import type { DmDevice } from "../types/device";
import { CrudClient } from "./crud-client";

export class DeviceClient extends CrudClient<DmDevice> {
  constructor() {
    super("/devices");
  }

  /** Get all devices, optionally filtered by room. */
  override async getAll(roomId?: number | string): Promise<DmDevice[]> {
    const query =
      roomId !== undefined && roomId !== ""
        ? `?room_id=${encodeURIComponent(String(roomId))}`
        : "";
    return super.getAll(query);
  }
}
