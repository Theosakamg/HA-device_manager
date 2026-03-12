/**
 * DmFloor - Second-level hierarchical entity representing a floor.
 */
import type { HierarchyEntity } from "./base";

export interface DmFloor extends HierarchyEntity {
  buildingId: number;
  /** Transient: parent building name (populated by API) */
  buildingName?: string;
}
