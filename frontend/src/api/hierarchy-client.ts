/**
 * API client for hierarchy tree operations.
 */
import type { HierarchyTree } from "../types/device";
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
}
