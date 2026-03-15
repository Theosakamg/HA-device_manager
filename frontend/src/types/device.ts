/**
 * Transient joined room data attached to a device by the repository JOIN query.
 */
export interface DeviceRoomRef {
  name: string;
  slug: string;
}

/**
 * Transient joined floor data attached to a device by the repository JOIN query.
 */
export interface DeviceFloorRef {
  name: string;
  slug: string;
  number: number;
}

/**
 * Transient joined building data attached to a device by the repository JOIN query.
 */
export interface DeviceBuildingRef {
  name: string;
  slug: string;
}

/**
 * Transient joined reference names (model, firmware, function, target).
 */
export interface DeviceLinkedRefs {
  modelName: string;
  firmwareName: string;
  functionName: string;
  targetMac: string;
}

/**
 * DmDevice - The main device entity with foreign key references.
 * Transient joined data is grouped into nested objects (room, floor, building, refs)
 * instead of flat fields.
 */
export interface DmDevice {
  id?: number;
  mac: string;
  ip: string;
  enabled: boolean;
  state: "deployed" | "parking" | "out_of_order" | "deployed_hot";
  positionName: string;
  positionSlug: string;
  mode: string;
  interlock: string;
  haDeviceClass: string;
  extra: string;
  createdAt?: string;
  updatedAt?: string;
  /** FK to DmRoom */
  roomId: number;
  /** FK to DmDeviceModel */
  modelId: number;
  /** FK to DmDeviceFirmware */
  firmwareId: number;
  /** FK to DmDeviceFunction */
  functionId: number;
  /** FK to DmDevice (self-reference, nullable) */
  targetId?: number | null;
  /** Transient: nested joined objects populated by the repository JOIN */
  room?: DeviceRoomRef;
  floor?: DeviceFloorRef;
  building?: DeviceBuildingRef;
  refs?: DeviceLinkedRefs;
  /** Deploy tracking */
  lastDeployAt?: string | null;
  lastDeployStatus?: "done" | "fail" | null;
  /**
   * Short human-readable label: "Building > Floor > Room > Function > Position".
   * Computed server-side, present in full-detail API responses.
   */
  displayName?: string;
  /**
   * HTTP link to device (computed from IP).
   * Computed server-side, present in full-detail API responses.
   */
  link?: string | null;
  /**
   * MQTT topic for device communication.
   * Computed server-side, present in full-detail API responses.
   */
  mqttTopic?: string | null;
  /**
   * Device hostname.
   * Computed server-side, present in full-detail API responses.
   */
  hostname?: string | null;
  /**
   * Fully qualified domain name.
   * Computed server-side, present in full-detail API responses.
   */
  fqdn?: string | null;
}

/**
 * Computed device fields (not stored, calculated from device + hierarchy data).
 */
export interface ComputedDeviceFields {
  link: string | null;
  mqttTopic: string | null;
  hostname: string | null;
  fqdn: string | null;
  countTopic: number | null;
}

/**
 * Allowed device function values (single source of truth).
 */
export const DEVICE_FUNCTIONS = [
  "button",
  "door",
  "doorbell",
  "heater",
  "light",
  "motion",
  "shutter",
  "tv",
  "window",
  "thermal",
  "ir",
  "presence",
  "energy",
  "infra",
  "water",
  "gaz",
  "sensor",
] as const;

export type DeviceFunction = (typeof DEVICE_FUNCTIONS)[number] | string;

/**
 * Allowed device firmware values (single source of truth).
 */
export const DEVICE_FIRMWARES = [
  "embeded",
  "tasmota",
  "tuya",
  "zigbee",
  "na",
  "android",
  "android-cast",
  "wled",
] as const;

export type DeviceFirmware = (typeof DEVICE_FIRMWARES)[number] | string;

/**
 * Hierarchy tree node for the tree view.
 */
export interface HierarchyNode {
  type: "building" | "floor" | "room";
  id: number;
  name: string;
  slug: string;
  description?: string;
  image?: string;
  createdAt?: string;
  updatedAt?: string;
  deviceCount: number;
  children: HierarchyNode[];
}

/**
 * Full hierarchy tree response from the API.
 */
export interface HierarchyTree {
  buildings: HierarchyNode[];
  totalDevices: number;
}

/**
 * A single HA group created/updated by the generate endpoint.
 */
export interface HaGroup {
  entityId: string;
  name: string;
  memberCount: number;
  scope: "room" | "floor" | "building";
}

/**
 * Response from POST /api/device_manager/ha_groups/generate.
 */
export interface HaGroupsResult {
  groups: HaGroup[];
  total: number;
}

/**
 * A single HA floor created/updated by the sync endpoint.
 */
export interface HaFloor {
  floorId: string;
  name: string;
  level: number;
  slug: string;
}

/**
 * Response from POST /api/device_manager/ha_floors/sync.
 */
export interface HaFloorsResult {
  floors: HaFloor[];
  total: number;
}

/**
 * Import result from CSV import.
 */
export interface ImportResult {
  total: number;
  created: number;
  updated: number;
  skipped: number;
  errors: string[];
  logs: ImportLogEntry[];
}

export interface ImportLogEntry {
  row: number;
  status: "created" | "updated" | "skipped" | "error";
  message: string;
  id?: number;
  mac?: string;
}

/**
 * Deploy result showing firmware→device mapping.
 */
export interface DeployResult {
  totalDevices: number;
  firmwaresSelected: number;
  details: DeployFirmwareDetail[];
  errors: string[];
}

/** Detail per firmware in a deploy operation. */
export interface DeployFirmwareDetail {
  firmwareId: number;
  firmwareName: string;
  deviceCount: number;
  devices: { mac: string; positionName: string }[];
}
