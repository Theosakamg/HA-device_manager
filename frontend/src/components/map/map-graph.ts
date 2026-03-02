/**
 * Graph building and Three.js rendering helpers for the Map View.
 *
 * Keeps pure data / scene logic separate from the LitElement component.
 */
import * as THREE from "three";
import type { HierarchyTree, DmDevice } from "../../types/device";
import type { DmDeviceFirmware } from "../../types/device-firmware";
import type { DmDeviceModel } from "../../types/device-model";
import type { DmDeviceFunction } from "../../types/device-function";
import {
  type GraphNode, type GraphEdge, type MapStats,
  COLORS, FIRMWARE_COLORS, FUNCTION_COLORS, MODEL_PALETTE,
  REF_EDGE_COLORS, NODE_RADIUS, TIER_Y, REF_CLUSTER,
} from "./map-constants";

/* ------------------------------------------------------------------ */
/*  Graph builder                                                       */
/* ------------------------------------------------------------------ */

/**
 * Build the full node/edge/stats dataset from raw API data.
 * Pure function – no Three.js, no side-effects.
 */
export function buildGraphData(
  tree: HierarchyTree,
  devices: DmDevice[],
  firmwares: DmDeviceFirmware[],
  models: DmDeviceModel[],
  functions: DmDeviceFunction[],
  layoutMode: "spiral" | "linear",
): { nodes: GraphNode[]; edges: GraphEdge[]; stats: MapStats } {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];

  /* ---- 1) Hierarchy: Home → Level → Room → Device ---- */
  const homeCount = tree.homes.length;
  const homeAngleStep = (Math.PI * 2) / Math.max(homeCount, 1);

  tree.homes.forEach((home, homeIdx) => {
    const hAngle = homeAngleStep * homeIdx;
    const hRadius = 14;
    const hx = layoutMode === "linear"
      ? (homeIdx - (homeCount - 1) / 2) * 22
      : Math.cos(hAngle) * hRadius;
    const hz = layoutMode === "linear" ? 0 : Math.sin(hAngle) * hRadius;

    const homeId = `home-${home.id}`;
    nodes.push({
      id: homeId, label: home.name, type: "home",
      color: COLORS.home, radius: NODE_RADIUS.home,
      position: new THREE.Vector3(hx, TIER_Y.home, hz),
      meta: `${home.deviceCount} devices`, homeId,
    });

    const levelCount = home.children.length;
    home.children.forEach((level, levelIdx) => {
      const lAngle  = hAngle + (levelIdx - (levelCount - 1) / 2) * 0.55;
      const lRadius = 8;
      const lx = layoutMode === "linear"
        ? hx + (levelIdx - (levelCount - 1) / 2) * 6
        : hx + Math.cos(lAngle) * lRadius;
      const lz = layoutMode === "linear" ? 0 : hz + Math.sin(lAngle) * lRadius;

      const levelId = `level-${level.id}`;
      nodes.push({
        id: levelId, label: level.name, type: "level",
        color: COLORS.level, radius: NODE_RADIUS.level,
        position: new THREE.Vector3(lx, TIER_Y.level, lz),
        meta: `${level.deviceCount} devices`, homeId,
      });
      edges.push({ source: homeId, target: levelId, edgeType: "hierarchy" });

      const roomCount = level.children.length;
      level.children.forEach((room, roomIdx) => {
        const rAngle  = lAngle + (roomIdx - (roomCount - 1) / 2) * 0.45;
        const rRadius = 6;
        const rx = layoutMode === "linear"
          ? lx + (roomIdx - (roomCount - 1) / 2) * 3.5
          : lx + Math.cos(rAngle) * rRadius;
        const rz = layoutMode === "linear" ? 0 : lz + Math.sin(rAngle) * rRadius;

        const roomId = `room-${room.id}`;
        nodes.push({
          id: roomId, label: room.name, type: "room",
          color: COLORS.room, radius: NODE_RADIUS.room,
          position: new THREE.Vector3(rx, TIER_Y.room, rz),
          meta: `${room.deviceCount} devices`, homeId,
        });
        edges.push({ source: levelId, target: roomId, edgeType: "hierarchy" });

        const roomDevices = devices.filter((d) => d.roomId === room.id);
        const devCount = roomDevices.length;
        roomDevices.forEach((dev, devIdx) => {
          const dAngle  = rAngle + (devIdx - (devCount - 1) / 2) * 0.35;
          const dRadius = 4;
          const dx = layoutMode === "linear"
            ? rx + (devIdx - (devCount - 1) / 2) * 2
            : rx + Math.cos(dAngle) * dRadius;
          const dz = layoutMode === "linear" ? 0 : rz + Math.sin(dAngle) * dRadius;

          const deviceId = `device-${dev.id}`;
          nodes.push({
            id: deviceId, label: dev.positionName || dev.mac, type: "device",
            color: COLORS.device, radius: NODE_RADIUS.device,
            position: new THREE.Vector3(dx, TIER_Y.device, dz),
            meta: `${dev.mac}\n${dev.firmwareName ?? ""} / ${dev.modelName ?? ""} / ${dev.functionName ?? ""}`,
            homeId,
          });
          edges.push({ source: roomId, target: deviceId, edgeType: "hierarchy" });

          if (dev.targetId) {
            edges.push({ source: deviceId, target: `device-${dev.targetId}`, edgeType: "target" });
          }
        });
      });
    });
  });

  /* ---- 2) Reference nodes: Firmware / Model / Function ---- */
  const placeCluster = (
    items: { id: string; label: string; type: "firmware" | "model" | "function"; color: number; meta: string }[],
  ) => {
    const clusterType = items[0]?.type;
    if (!clusterType) return;
    const centre = REF_CLUSTER[clusterType];
    const count = items.length;
    const clusterRadius = Math.max(3, count * 0.8);
    const angleStep = (Math.PI * 2) / Math.max(count, 1);
    items.forEach((item, idx) => {
      const angle = angleStep * idx;
      nodes.push({
        id: item.id, label: item.label, type: item.type, color: item.color,
        radius: NODE_RADIUS[item.type],
        position: new THREE.Vector3(
          centre.x + Math.cos(angle) * clusterRadius,
          TIER_Y[item.type],
          centre.z + Math.sin(angle) * clusterRadius,
        ),
        meta: item.meta,
      });
    });
  };

  placeCluster(firmwares.map((fw) => ({
    id: `firmware-${fw.id}`, label: fw.name, type: "firmware" as const,
    color: FIRMWARE_COLORS[fw.name.toLowerCase()] ?? COLORS.firmware,
    meta: `Firmware\n${devices.filter((d) => d.firmwareId === fw.id).length} device(s)`,
  })));

  placeCluster(models.map((m, idx) => ({
    id: `model-${m.id}`, label: m.name, type: "model" as const,
    color: MODEL_PALETTE[idx % MODEL_PALETTE.length],
    meta: `Model\n${devices.filter((d) => d.modelId === m.id).length} device(s)`,
  })));

  placeCluster(functions.map((fn) => ({
    id: `function-${fn.id}`, label: fn.name, type: "function" as const,
    color: FUNCTION_COLORS[fn.name.toLowerCase()] ?? COLORS.function,
    meta: `Function\n${devices.filter((d) => d.functionId === fn.id).length} device(s)`,
  })));

  /* ---- 3) Reference edges: Device → Firmware / Model / Function ---- */
  const nodeIds = new Set(nodes.map((n) => n.id));
  for (const dev of devices) {
    const deviceId = `device-${dev.id}`;
    if (!nodeIds.has(deviceId)) continue;
    if (dev.firmwareId) edges.push({ source: deviceId, target: `firmware-${dev.firmwareId}`, edgeType: "firmware" });
    if (dev.modelId)    edges.push({ source: deviceId, target: `model-${dev.modelId}`,       edgeType: "model" });
    if (dev.functionId) edges.push({ source: deviceId, target: `function-${dev.functionId}`, edgeType: "function" });
  }

  const stats: MapStats = {
    homes:     tree.homes.length,
    levels:    tree.homes.reduce((s, h) => s + h.children.length, 0),
    rooms:     tree.homes.reduce((s, h) => s + h.children.reduce((ss, l) => ss + l.children.length, 0), 0),
    devices:   devices.length,
    firmwares: firmwares.length,
    models:    models.length,
    functions: functions.length,
  };

  return { nodes, edges, stats };
}

/* ------------------------------------------------------------------ */
/*  Three.js rendering helpers                                         */
/* ------------------------------------------------------------------ */

/** Create Three.js meshes / sprites for nodes and edge lines. Mutates node.mesh, edge.line. */
export function renderGraphToScene(
  scene: THREE.Scene,
  nodes: GraphNode[],
  edges: GraphEdge[],
  maxAnisotropy: number,
): void {
  const nodeMap = new Map<string, GraphNode>();

  for (const node of nodes) {
    nodeMap.set(node.id, node);

    const geometry = _nodeGeometry(node.type, node.radius);
    const material = new THREE.MeshStandardMaterial({
      color: node.color,
      roughness: 0.25, metalness: 0.5,
      emissive: new THREE.Color(node.color), emissiveIntensity: 0.25,
      transparent: true, opacity: 1, depthWrite: true,
    });
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.copy(node.position);
    mesh.userData = { nodeId: node.id };
    node.mesh = mesh;
    scene.add(mesh);

    // Halo ring for prominent node types
    if (["home", "level", "firmware", "model", "function"].includes(node.type)) {
      const ring = new THREE.Mesh(
        new THREE.RingGeometry(node.radius * 1.2, node.radius * 1.6, 32),
        new THREE.MeshBasicMaterial({ color: node.color, transparent: true, opacity: 0.18, side: THREE.DoubleSide }),
      );
      ring.position.copy(node.position);
      ring.rotation.x = Math.PI / 2;
      scene.add(ring);
    }

    const sprite = makeLabel(node.label, node.color, maxAnisotropy);
    sprite.position.copy(node.position);
    sprite.position.y += node.radius + 1.2;
    node.labelSprite = sprite;
    scene.add(sprite);
  }

  for (const edge of edges) {
    const src = nodeMap.get(edge.source);
    const tgt = nodeMap.get(edge.target);
    if (!src || !tgt) continue;

    const isRef = edge.edgeType === "firmware" || edge.edgeType === "model" || edge.edgeType === "function";
    const line = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(curvedEdge(src.position, tgt.position)),
      new THREE.LineBasicMaterial({
        color: isRef ? (REF_EDGE_COLORS[edge.edgeType!] ?? COLORS.edge) : 0x64748b,
        transparent: true, opacity: isRef ? 0.22 : 0.35,
      }),
    );
    edge.line = line;
    scene.add(line);
  }
}

/** Return the appropriate geometry for a node type. */
function _nodeGeometry(type: GraphNode["type"], radius: number): THREE.BufferGeometry {
  switch (type) {
    case "home":     return new THREE.IcosahedronGeometry(radius, 1);
    case "level":    return new THREE.OctahedronGeometry(radius, 0);
    case "room":     return new THREE.DodecahedronGeometry(radius, 0);
    case "firmware": return new THREE.CylinderGeometry(radius, radius, radius * 0.8, 6);
    case "model":    return new THREE.BoxGeometry(radius * 1.4, radius * 1.4, radius * 1.4);
    case "function": return new THREE.ConeGeometry(radius, radius * 1.6, 8);
    default:         return new THREE.SphereGeometry(radius, 16, 16);
  }
}

/** Create a canvas text sprite for a node label. */
export function makeLabel(text: string, color: number, maxAnisotropy: number): THREE.Sprite {
  const canvas = document.createElement("canvas");
  canvas.width = 1024; canvas.height = 192;
  const ctx = canvas.getContext("2d")!;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.font = `bold 96px Arial, sans-serif`;
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  ctx.shadowColor = `#${color.toString(16).padStart(6, "0")}`;
  ctx.shadowBlur = 14;
  ctx.fillStyle = "#1e293b";
  ctx.fillText(text, canvas.width / 2, canvas.height / 2);

  const tex = new THREE.CanvasTexture(canvas);
  tex.minFilter = tex.magFilter = THREE.LinearFilter;
  tex.anisotropy = maxAnisotropy;
  tex.needsUpdate = true;

  const sprite = new THREE.Sprite(
    new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false }),
  );
  sprite.scale.set(6, 1.2, 1);
  return sprite;
}

/** Quadratic bezier curve between two world positions. */
export function curvedEdge(a: THREE.Vector3, b: THREE.Vector3): THREE.Vector3[] {
  const mid = a.clone().lerp(b, 0.5);
  mid.y += 2;
  return new THREE.QuadraticBezierCurve3(a, mid, b).getPoints(20);
}

/** Add a star-field particle system to the scene and return it. */
export function addStarField(scene: THREE.Scene): THREE.Points {
  const count = 1500;
  const positions = new Float32Array(count * 3).map(() => (Math.random() - 0.5) * 200);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const system = new THREE.Points(geo, new THREE.PointsMaterial({
    color: 0x94a3b8, size: 0.15, transparent: true, opacity: 0.25,
  }));
  scene.add(system);
  return system;
}
