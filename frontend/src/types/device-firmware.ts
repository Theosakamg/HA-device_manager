/**
 * DmDeviceFirmware - Reference entity for firmware types.
 */
import type { NamedEntity } from "./base";

export interface DmDeviceFirmware extends NamedEntity {
  /** Whether this firmware can be targeted by the deploy process. */
  deployable: boolean;
}
