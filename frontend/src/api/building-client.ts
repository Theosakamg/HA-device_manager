/**
 * API client for DmBuilding CRUD operations.
 */
import type { DmBuilding } from "../types/building";
import { CrudClient } from "./crud-client";

export class BuildingClient extends CrudClient<DmBuilding> {
  constructor() {
    super("/buildings");
  }
}
