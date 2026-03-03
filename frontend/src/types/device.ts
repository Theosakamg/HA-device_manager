/**
 * DmDevice - The main device entity with foreign key references.
 */
export interface DmDevice {
  id?: number;
  mac: string;
  ip: string;
  enabled: boolean;
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
  /** Transient: joined data from related entities */
  roomName?: string;
  roomSlug?: string;
  floorName?: string;
  floorSlug?: string;
  floorNumber?: number;
  buildingName?: string;
  modelName?: string;
  firmwareName?: string;
  functionName?: string;
  targetMac?: string;
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
