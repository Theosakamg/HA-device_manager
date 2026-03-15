/**
 * API client for hierarchy tree operations.
 */
import type {
  HierarchyTree,
  HaGroupsResult,
  HaFloorsResult,
  HaRoomsResult,
} from "../types/device";
import { BaseClient } from "./base-client";

export class HierarchyClient extends BaseClient {
  /** Get the full hierarchy tree (buildings → floors → rooms with device counts). */
  async getTree(): Promise<HierarchyTree> {
    return this.get<HierarchyTree>("/hierarchy");
  }

  /** Get a subtree for a specific building. */
  async getBuildingTree(buildingId: number): Promise<HierarchyTree> {
    return this.get<HierarchyTree>(`/buildings/${buildingId}/tree`);
  }

  /** Generate HA groups for ALL buildings (full room → floor → building stack). */
  async generateHaGroups(): Promise<HaGroupsResult> {
    return this.post<HaGroupsResult>("/ha_groups/generate", {});
  }

  /** Synchronize all Device Manager floors to the HA native floor registry. */
  async syncHaFloors(): Promise<HaFloorsResult> {
    return this.post<HaFloorsResult>("/ha_floors/sync", {});
  }

  /** Synchronize all Device Manager rooms to the HA native area registry. */
  async syncHaRooms(): Promise<HaRoomsResult> {
    return this.post<HaRoomsResult>("/ha_rooms/sync", {});
  }
}
