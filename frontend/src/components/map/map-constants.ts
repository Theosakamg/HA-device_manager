/**
 * Shared types, interfaces, and constants for the Map View.
 */
import type * as THREE from "three";

/* ------------------------------------------------------------------ */
/*  Types                                                               */
/* ------------------------------------------------------------------ */

export interface GraphNode {
  id: string;
  label: string;
  type: "home" | "level" | "room" | "device" | "firmware" | "model" | "function";
  color: number;
  radius: number;
  mesh?: THREE.Mesh;
  labelSprite?: THREE.Sprite;
  position: THREE.Vector3;
  /** Extra info for tooltip */
  meta: string;
  /** Parent home id (for filtering) */
  homeId?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  edgeType?: "hierarchy" | "firmware" | "model" | "function" | "target";
  line?: THREE.Line;
}

export interface MapStats {
  homes: number;
  levels: number;
  rooms: number;
  devices: number;
  firmwares: number;
  models: number;
  functions: number;
}

/* ------------------------------------------------------------------ */
/*  Colour palettes                                                     */
/* ------------------------------------------------------------------ */

/** Colour palette per node type */
export const COLORS = {
  home:     0xfbbf24, // amber / gold
  level:    0x14b8a6, // teal
  room:     0x6366f1, // indigo
  device:   0x64748b, // slate-500
  firmware: 0x22d3ee, // cyan
  model:    0xfb923c, // orange
  function: 0xa78bfa, // violet
  edge:     0x94a3b8, // slate-400
} as const;

export const FIRMWARE_COLORS: Record<string, number> = {
  tasmota:        0x22d3ee,
  zigbee:         0xa78bfa,
  tuya:           0xfb923c,
  embeded:        0x34d399,
  wled:           0xf472b6,
  android:        0x60a5fa,
  "android-cast": 0x818cf8,
  na:             0x94a3b8,
};

export const FUNCTION_COLORS: Record<string, number> = {
  button:   0xfbbf24,
  door:     0x8b5cf6,
  doorbell: 0xf59e0b,
  heater:   0xef4444,
  light:    0xfcd34d,
  motion:   0x10b981,
  shutter:  0x6366f1,
  tv:       0x3b82f6,
  window:   0x06b6d4,
  thermal:  0xf97316,
  ir:       0xec4899,
  presence: 0x14b8a6,
  energy:   0x84cc16,
  infra:    0xa855f7,
  water:    0x0ea5e9,
  gaz:      0xd946ef,
  sensor:   0x64748b,
};

/** Rotating palette for model reference nodes */
export const MODEL_PALETTE = [
  0xfb923c, 0x38bdf8, 0xa3e635, 0xfbbf24, 0xf472b6,
  0x34d399, 0xc084fc, 0x22d3ee, 0xf87171, 0x818cf8,
  0x4ade80, 0xfacc15, 0x2dd4bf, 0xe879f9, 0x67e8f9,
];

export const REF_EDGE_COLORS: Record<string, number> = {
  firmware: 0x22d3ee,
  model:    0xfb923c,
  function: 0xa78bfa,
};

/* ------------------------------------------------------------------ */
/*  Layout constants                                                    */
/* ------------------------------------------------------------------ */

export const NODE_RADIUS: Record<string, number> = {
  home:     2.0,
  level:    1.4,
  room:     1.0,
  device:   0.5,
  firmware: 0.85,
  model:    0.85,
  function: 0.85,
};

export const TIER_Y: Record<string, number> = {
  home:     12,
  level:    4,
  room:     -4,
  device:   -12,
  firmware: -22,
  model:    -22,
  function: -22,
};

export const REF_CLUSTER: Record<string, { x: number; z: number }> = {
  firmware: { x: -28, z: 0 },
  model:    { x: 0,   z: -28 },
  function: { x: 28,  z: 0 },
};
