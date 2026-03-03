/**
 * API client for DmRoom CRUD operations.
 */
import type { DmRoom } from "../types/room";
import { CrudClient } from "./crud-client";

export class RoomClient extends CrudClient<DmRoom> {
  constructor() {
    super("/rooms");
  }

  /** Get all rooms, optionally filtered by floor. */
  override async getAll(floorId?: number | string): Promise<DmRoom[]> {
    const query =
      floorId !== undefined && floorId !== ""
        ? `?floor_id=${encodeURIComponent(String(floorId))}`
        : "";
    return super.getAll(query);
  }
}
