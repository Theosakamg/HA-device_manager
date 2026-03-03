/**
 * Base entity interfaces shared across all domain models.
 */

/** Common fields for all persisted entities. */
export interface BaseEntity {
  id?: number;
  createdAt?: string;
  updatedAt?: string;
}

/** Reference entity with name and enabled flag (firmware, function, model). */
export interface NamedEntity extends BaseEntity {
  name: string;
  enabled: boolean;
}

/** Hierarchical entity with name, slug, description, image (home, level, room). */
export interface HierarchyEntity extends BaseEntity {
  name: string;
  slug: string;
  description?: string;
  image?: string;
}
