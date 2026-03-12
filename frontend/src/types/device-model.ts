/**
 * DmDeviceModel - Reference entity for device models/hardware types.
 */
import type { NamedEntity } from "./base";

export interface DmDeviceModel extends NamedEntity {
  template?: string;
}
