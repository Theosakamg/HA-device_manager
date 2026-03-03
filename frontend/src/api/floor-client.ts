/**
 * API client for DmFloor CRUD operations.
 */
import type { DmFloor } from "../types/floor";
import { CrudClient } from "./crud-client";

export class FloorClient extends CrudClient<DmFloor> {
  constructor() {
    super("/floors");
  }

  /** Get all floors, optionally filtered by building. */
  override async getAll(buildingId?: number | string): Promise<DmFloor[]> {
    const query =
      buildingId !== undefined && buildingId !== ""
        ? `?building_id=${encodeURIComponent(String(buildingId))}`
        : "";
    return super.getAll(query);
  }
}
