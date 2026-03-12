/**
 * DmRoom - Third-level hierarchical entity representing a room.
 */
import type { HierarchyEntity } from "./base";

export interface DmRoom extends HierarchyEntity {
  floorId: number;
  /** Optional login credential for room equipment. */
  login?: string;
  /** Optional password stored encrypted at rest on the server. */
  password?: string;
  /** Transient: parent floor name (populated by API) */
  floorName?: string;
}
