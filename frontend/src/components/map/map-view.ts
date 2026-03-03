/**
 * Map View – Interactive 3D visualization of the full device model.
 *
 * Renders the DB model relationships as an orbiting 3D graph:
 *   Hierarchy  : Building → Floor → Room → Device
 *   References : Device → Firmware / Model / Function
 */
import { LitElement, html } from "lit";
import { customElement, state } from "lit/decorators.js";
import { sharedStyles } from "../../styles/shared-styles";
import { i18n, localized } from "../../i18n";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { HierarchyClient } from "../../api/hierarchy-client";
import { DeviceClient } from "../../api/device-client";
import { DeviceFirmwareClient } from "../../api/device-firmware-client";
import { DeviceModelClient } from "../../api/device-model-client";
import { DeviceFunctionClient } from "../../api/device-function-client";
import type { HierarchyTree, DmDevice } from "../../types/device";
import type { DmDeviceFirmware } from "../../types/device-firmware";
import type { DmDeviceModel } from "../../types/device-model";
import type { DmDeviceFunction } from "../../types/device-function";
import {
  type GraphNode,
  type GraphEdge,
  type MapStats,
  COLORS,
  REF_EDGE_COLORS,
} from "./map-constants";
import { mapStyles } from "./map-styles";
import { buildGraphData, renderGraphToScene, addStarField } from "./map-graph";

/* ------------------------------------------------------------------ */
/*  Helpers                                                             */
/* ------------------------------------------------------------------ */
const easeInOut = (t: number) =>
  t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;

/* ------------------------------------------------------------------ */
/*  Component                                                           */
/* ------------------------------------------------------------------ */

@localized
@customElement("dm-map-view")
export class DmMapView extends LitElement {
  static styles = [sharedStyles, mapStyles];

  /* ---- reactive state ---- */
  @state() private _loading = true;
  @state() private _isFullscreen = false;
  @state() private _stats: MapStats = {
    buildings: 0,
    floors: 0,
    rooms: 0,
    devices: 0,
    firmwares: 0,
    models: 0,
    functions: 0,
  };
  @state() private _layoutMode: "spiral" | "linear" = "spiral";
  @state() private _debugVisible = false;
  /** Empty array = no filter (show all). */
  @state() private _filterHome: string[] = [];
  @state() private _filterFirmware: string[] = [];
  @state() private _filterModel: string[] = [];
  @state() private _filterFunction: string[] = [];
  @state() private _homeOptions: { id: string; name: string }[] = [];
  @state() private _firmwareOptions: { id: string; name: string }[] = [];
  @state() private _modelOptions: { id: string; name: string }[] = [];
  @state() private _functionOptions: { id: string; name: string }[] = [];

  /* ---- Three.js ---- */
  private _scene!: THREE.Scene;
  private _camera!: THREE.PerspectiveCamera;
  private _renderer!: THREE.WebGLRenderer;
  private _controls!: OrbitControls;
  private _animId = 0;
  private _nodes: GraphNode[] = [];
  private _edges: GraphEdge[] = [];
  private _raycaster = new THREE.Raycaster();
  private _mouse = new THREE.Vector2();
  private _hoveredNode: GraphNode | null = null;
  private _particleSystem?: THREE.Points;
  private _clock = new THREE.Clock();
  private _initialized = false;
  private _disposed = false;

  /* ---- focus ---- */
  private _focusedNode: GraphNode | null = null;
  private _focusRing?: THREE.Mesh;
  private _focusRelatedCache: Set<string> | null = null;

  /* ---- fly-to animation ---- */
  private _flyAnimating = false;
  private _flyFrom = new THREE.Vector3();
  private _flyTo = new THREE.Vector3();
  private _flyFromLookAt = new THREE.Vector3();
  private _flyTargetLookAt = new THREE.Vector3();
  private _flyDuration = 1.2;
  private _flyStartTime = 0;

  /* ---- ViewCube ---- */
  private _vcScene!: THREE.Scene;
  private _vcCamera!: THREE.PerspectiveCamera;
  private _vcRenderer!: THREE.WebGLRenderer;
  private _vcCube!: THREE.Mesh;

  /* ---- debug perf ---- */
  private _dbgFrameCount = 0;
  private _dbgLastTime = 0;
  private _dbgFps = 0;
  private _gpuRenderer = "";
  private _gpuVendor = "";

  /* ---- raw data (for filter rebuilds) ---- */
  private _rawTree!: HierarchyTree;
  private _rawDevices: DmDevice[] = [];
  private _rawFirmwares: DmDeviceFirmware[] = [];
  private _rawModels: DmDeviceModel[] = [];
  private _rawFunctions: DmDeviceFunction[] = [];

  /* ---- click vs drag ---- */
  private _mouseDownPos = { x: 0, y: 0 };
  private static DRAG_THRESHOLD = 5;

  /* ---- API clients ---- */
  private _hierarchyClient = new HierarchyClient();
  private _deviceClient = new DeviceClient();
  private _firmwareClient = new DeviceFirmwareClient();
  private _modelClient = new DeviceModelClient();
  private _functionClient = new DeviceFunctionClient();

  /* ================================================================ */
  /*  Lifecycle                                                       */
  /* ================================================================ */

  async connectedCallback() {
    super.connectedCallback();
    await this.updateComplete;
    requestAnimationFrame(() => this._init());
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    this._disposed = true;
    cancelAnimationFrame(this._animId);
    this._animId = 0;

    window.removeEventListener("resize", this._onResize);
    const canvas = this._renderer?.domElement;
    if (canvas) {
      canvas.removeEventListener("mousemove", this._onMouseMove);
      canvas.removeEventListener("mousedown", this._onMouseDown);
      canvas.removeEventListener("mouseup", this._onMouseUp);
    }

    this._clearScene();
    this._removeFocusRing();
    if (this._particleSystem) {
      this._particleSystem.geometry.dispose();
      (this._particleSystem.material as THREE.Material).dispose();
      this._particleSystem = undefined;
    }
    this._controls?.dispose();
    this._renderer?.dispose();
    this._renderer?.forceContextLoss();
    this._vcRenderer?.dispose();
    this._vcRenderer?.forceContextLoss();
    this._nodes = [];
    this._edges = [];
    this._hoveredNode = null;
    this._focusedNode = null;
    this._focusRelatedCache = null;
    this._flyAnimating = false;
    this._initialized = false;
  }

  private _clearScene() {
    for (const node of this._nodes) {
      if (node.mesh) {
        node.mesh.geometry.dispose();
        (node.mesh.material as THREE.Material).dispose();
        this._scene?.remove(node.mesh);
        node.mesh = undefined;
      }
      if (node.labelSprite) {
        const mat = node.labelSprite.material as THREE.SpriteMaterial;
        mat.map?.dispose();
        mat.dispose();
        this._scene?.remove(node.labelSprite);
        node.labelSprite = undefined;
      }
    }
    for (const edge of this._edges) {
      if (edge.line) {
        edge.line.geometry.dispose();
        (edge.line.material as THREE.Material).dispose();
        this._scene?.remove(edge.line);
        edge.line = undefined;
      }
    }
    // Remove untracked halo rings
    if (this._scene) {
      const toRemove: THREE.Object3D[] = [];
      this._scene.traverse((obj) => {
        if (
          obj instanceof THREE.Mesh &&
          !obj.userData.nodeId &&
          obj !== this._focusRing
        )
          toRemove.push(obj);
      });
      for (const obj of toRemove) {
        if (obj instanceof THREE.Mesh) {
          obj.geometry.dispose();
          (obj.material as THREE.Material).dispose();
        }
        this._scene.remove(obj);
      }
    }
  }

  /* ================================================================ */
  /*  Init                                                             */
  /* ================================================================ */

  private async _init() {
    if (this._initialized) return;
    this._disposed = false;

    const wrap =
      this.shadowRoot!.querySelector<HTMLDivElement>(".canvas-wrap")!;
    const canvas = wrap.querySelector<HTMLCanvasElement>("canvas")!;

    this._renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: "high-performance",
    });
    this._renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this._renderer.setSize(wrap.clientWidth, wrap.clientHeight);

    // GPU info
    try {
      const gl = this._renderer.getContext() as WebGL2RenderingContext;
      const dbg = gl.getExtension("WEBGL_debug_renderer_info");
      if (dbg) {
        this._gpuVendor = gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL);
        this._gpuRenderer = gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL);
      } else {
        this._gpuRenderer = this._renderer.capabilities.isWebGL2
          ? "WebGL2"
          : "WebGL1";
        this._gpuVendor = "(info non disponible)";
      }
    } catch {
      this._gpuRenderer = this._gpuVendor = "inconnu";
    }

    this._scene = new THREE.Scene();
    this._scene.fog = new THREE.FogExp2(0xd1d5db, 0.0008);

    this._camera = new THREE.PerspectiveCamera(
      55,
      wrap.clientWidth / wrap.clientHeight,
      0.1,
      500
    );
    this._camera.position.set(0, 24, 55);

    this._controls = new OrbitControls(this._camera, canvas);
    Object.assign(this._controls, {
      enableDamping: true,
      dampingFactor: 0.08,
      minDistance: 8,
      maxDistance: 180,
      autoRotate: true,
      autoRotateSpeed: 0.4,
    });

    this._scene.add(new THREE.AmbientLight(0xffffff, 0.75));
    const p1 = new THREE.PointLight(0xfbbf24, 1.2, 120);
    p1.position.set(20, 30, 20);
    this._scene.add(p1);
    const p2 = new THREE.PointLight(0x6366f1, 0.8, 120);
    p2.position.set(-20, -10, -20);
    this._scene.add(p2);

    this._particleSystem = addStarField(this._scene);

    window.addEventListener("resize", this._onResize);
    canvas.addEventListener("mousemove", this._onMouseMove);
    canvas.addEventListener("mousedown", this._onMouseDown);
    canvas.addEventListener("mouseup", this._onMouseUp);
    wrap.addEventListener("fullscreenchange", this._onFullscreenChange);

    this._initViewCube(wrap);
    this._initialized = true;

    await this._loadData();
    if (!this._disposed) this._animate();
  }

  /* ================================================================ */
  /*  Data                                                             */
  /* ================================================================ */

  private async _loadData() {
    try {
      const [tree, devices, firmwares, models, functions] = await Promise.all([
        this._hierarchyClient.getTree(),
        this._deviceClient.getAll(),
        this._firmwareClient.getAll(),
        this._modelClient.getAll(),
        this._functionClient.getAll(),
      ]);
      this._rawTree = tree;
      this._rawDevices = devices;
      this._rawFirmwares = firmwares;
      this._rawModels = models;
      this._rawFunctions = functions;

      const byName = (a: { name: string }, b: { name: string }) =>
        a.name.localeCompare(b.name);
      this._homeOptions = tree.buildings
        .map((h) => ({ id: String(h.id), name: h.name }))
        .sort(byName);
      this._firmwareOptions = firmwares
        .map((fw) => ({ id: String(fw.id), name: fw.name }))
        .sort(byName);
      this._modelOptions = models
        .map((m) => ({ id: String(m.id), name: m.name }))
        .sort(byName);
      this._functionOptions = functions
        .map((fn) => ({ id: String(fn.id), name: fn.name }))
        .sort(byName);

      this._buildGraph(tree, devices, firmwares, models, functions);
      this._loading = false;
    } catch (err) {
      console.error("Map: failed to load data", err);
      this._loading = false;
    }
  }

  private _buildGraph(
    tree: HierarchyTree,
    devices: DmDevice[],
    firmwares: DmDeviceFirmware[],
    models: DmDeviceModel[],
    functions: DmDeviceFunction[]
  ) {
    const { nodes, edges, stats } = buildGraphData(
      tree,
      devices,
      firmwares,
      models,
      functions,
      this._layoutMode
    );
    this._nodes = nodes;
    this._edges = edges;
    this._stats = stats;
    renderGraphToScene(
      this._scene,
      this._nodes,
      this._edges,
      this._renderer.capabilities.getMaxAnisotropy()
    );
  }

  /* ================================================================ */
  /*  Focus system                                                     */
  /* ================================================================ */

  private _focusOn(node: GraphNode) {
    this._controls.autoRotate = false;
    const related = this._getRelatedNodeIds(node.id);
    const relevant = this._nodes.filter(
      (n) => n.id === node.id || related.has(n.id)
    );

    const center = relevant
      .reduce((c, n) => c.add(n.position), new THREE.Vector3())
      .divideScalar(relevant.length || 1);
    let maxDist = 0;
    for (const n of relevant)
      maxDist = Math.max(maxDist, n.position.distanceTo(center));

    const fov = this._camera.fov * (Math.PI / 180);
    const fitDist = Math.max(maxDist + 2, 4) / Math.tan(fov / 2);
    const dir = this._camera.position
      .clone()
      .sub(this._controls.target)
      .normalize();
    const targetPos = center
      .clone()
      .add(dir.multiplyScalar(Math.min(Math.max(fitDist, 8), 120)));

    this._startFly(targetPos, center);
  }

  private _showFocusRing(node: GraphNode) {
    this._removeFocusRing();
    const r = node.radius * 2.2;
    this._focusRing = new THREE.Mesh(
      new THREE.RingGeometry(r * 0.85, r, 48),
      new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 0.35,
        side: THREE.DoubleSide,
      })
    );
    this._focusRing.position.copy(node.mesh!.position);
    this._focusRing.rotation.x = Math.PI / 2;
    this._scene.add(this._focusRing);
  }

  private _removeFocusRing() {
    if (this._focusRing) {
      this._scene.remove(this._focusRing);
      this._focusRing.geometry.dispose();
      (this._focusRing.material as THREE.Material).dispose();
      this._focusRing = undefined;
    }
  }

  private _releaseFocus() {
    if (this._focusedNode?.mesh)
      (
        this._focusedNode.mesh.material as THREE.MeshStandardMaterial
      ).emissiveIntensity = 0.25;
    this._clearFocusDimming();
    this._removeFocusRing();
    this._focusedNode = null;
    this._focusRelatedCache = null;
    this._controls.autoRotate = true;
  }

  private _getRelatedNodeIds(nodeId: string): Set<string> {
    const related = new Set<string>();
    const childrenOf = new Map<string, string[]>();
    const parentsOf = new Map<string, string[]>();
    for (const e of this._edges) {
      (
        childrenOf.get(e.source) ??
        (childrenOf.set(e.source, []), childrenOf.get(e.source)!)
      ).push(e.target);
      (
        parentsOf.get(e.target) ??
        (parentsOf.set(e.target, []), parentsOf.get(e.target)!)
      ).push(e.source);
    }
    const bfs = (start: string, map: Map<string, string[]>) => {
      const q = [start];
      while (q.length)
        for (const n of map.get(q.shift()!) ?? [])
          if (!related.has(n)) {
            related.add(n);
            q.push(n);
          }
    };
    bfs(nodeId, childrenOf);
    bfs(nodeId, parentsOf);
    return related;
  }

  private _applyFocusDimming(focusedId: string) {
    const related = this._getRelatedNodeIds(focusedId);
    for (const node of this._nodes) {
      if (!node.mesh) continue;
      const mat = node.mesh.material as THREE.MeshStandardMaterial;
      if (node.id === focusedId) {
        mat.emissiveIntensity = 1;
        mat.opacity = 1;
        mat.depthWrite = true;
        if (node.labelSprite) node.labelSprite.material.opacity = 1;
      } else if (related.has(node.id)) {
        mat.emissiveIntensity = 0.6;
        mat.opacity = 1;
        mat.depthWrite = true;
        if (node.labelSprite) node.labelSprite.material.opacity = 0.9;
      } else {
        mat.emissiveIntensity = 0;
        mat.opacity = 0.015;
        mat.depthWrite = false;
        if (node.labelSprite) node.labelSprite.material.opacity = 0.008;
      }
    }
    for (const edge of this._edges) {
      if (!edge.line) continue;
      const mat = edge.line.material as THREE.LineBasicMaterial;
      const isRef =
        edge.edgeType === "firmware" ||
        edge.edgeType === "model" ||
        edge.edgeType === "function";
      const active =
        (edge.source === focusedId || related.has(edge.source)) &&
        (edge.target === focusedId || related.has(edge.target));
      mat.opacity = active ? 0.9 : 0.008;
      mat.color.set(
        active
          ? isRef
            ? (REF_EDGE_COLORS[edge.edgeType!] ?? 0x475569)
            : 0x1e293b
          : COLORS.edge
      );
    }
  }

  private _clearFocusDimming() {
    for (const node of this._nodes) {
      if (!node.mesh) continue;
      const mat = node.mesh.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 0.25;
      mat.opacity = 1;
      mat.depthWrite = true;
      if (node.labelSprite) node.labelSprite.material.opacity = 1;
    }
    for (const edge of this._edges) {
      if (!edge.line) continue;
      const mat = edge.line.material as THREE.LineBasicMaterial;
      const isRef =
        edge.edgeType === "firmware" ||
        edge.edgeType === "model" ||
        edge.edgeType === "function";
      mat.opacity = isRef ? 0.22 : 0.35;
      mat.color.set(
        isRef ? (REF_EDGE_COLORS[edge.edgeType!] ?? 0x64748b) : 0x64748b
      );
    }
  }

  private _getBaseEmissive(node: GraphNode): number {
    if (!this._focusedNode) return 0.25;
    if (node === this._focusedNode) return 1;
    if (!this._focusRelatedCache)
      this._focusRelatedCache = this._getRelatedNodeIds(this._focusedNode.id);
    return this._focusRelatedCache.has(node.id) ? 0.6 : 0;
  }

  /* ================================================================ */
  /*  ViewCube                                                         */
  /* ================================================================ */

  private _initViewCube(wrap: HTMLDivElement) {
    const vcWrap = wrap.querySelector<HTMLDivElement>(".viewcube-wrap");
    if (!vcWrap) return;

    this._vcRenderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
    });
    this._vcRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this._vcRenderer.setSize(100, 100);
    this._vcRenderer.domElement.style.cssText = "width:100px;height:100px";
    vcWrap.appendChild(this._vcRenderer.domElement);

    this._vcScene = new THREE.Scene();
    this._vcCamera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
    this._vcCamera.position.set(0, 0, 4);
    this._vcScene.add(new THREE.AmbientLight(0xffffff, 0.9));
    const vcDir = new THREE.DirectionalLight(0xffffff, 0.6);
    vcDir.position.set(2, 3, 4);
    this._vcScene.add(vcDir);

    const faceLabels = ["Right", "Left", "Top", "Bottom", "Front", "Back"];
    this._vcCube = new THREE.Mesh(
      new THREE.BoxGeometry(1.6, 1.6, 1.6),
      faceLabels.map(
        (l) =>
          new THREE.MeshStandardMaterial({
            map: this._makeVCFaceTexture(l),
            roughness: 0.6,
            metalness: 0.1,
          })
      )
    );
    this._vcScene.add(this._vcCube);

    const vcRay = new THREE.Raycaster();
    const vcMouse = new THREE.Vector2();
    vcWrap.addEventListener("click", (e: MouseEvent) => {
      const rect = vcWrap.getBoundingClientRect();
      vcMouse.set(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );
      vcRay.setFromCamera(vcMouse, this._vcCamera);
      const hits = vcRay.intersectObject(this._vcCube);
      if (hits.length > 0) this._flyToViewCubeFace(hits[0].face!.materialIndex);
    });
  }

  private _makeVCFaceTexture(label: string): THREE.CanvasTexture {
    const size = 256;
    const c = document.createElement("canvas");
    c.width = c.height = size;
    const ctx = c.getContext("2d")!;
    ctx.fillStyle = "rgba(255,255,255,0.88)";
    ctx.fillRect(0, 0, size, size);
    ctx.strokeStyle = "#94a3b8";
    ctx.lineWidth = 4;
    ctx.strokeRect(2, 2, size - 4, size - 4);
    ctx.fillStyle = "#1e293b";
    ctx.font = "bold 72px Arial, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, size / 2, size / 2);
    const tex = new THREE.CanvasTexture(c);
    tex.needsUpdate = true;
    return tex;
  }

  private _flyToViewCubeFace(faceIdx: number) {
    const dirs: [number, number, number][] = [
      [1, 0, 0],
      [-1, 0, 0],
      [0, 1, 0],
      [0, -1, 0],
      [0, 0, 1],
      [0, 0, -1],
    ];
    const dir = new THREE.Vector3(...(dirs[faceIdx] ?? [0, 0, 1]));
    const target = this._controls.target.clone();
    this._controls.autoRotate = false;
    this._startFly(
      target
        .clone()
        .add(dir.multiplyScalar(this._camera.position.distanceTo(target))),
      target
    );
  }

  /* ================================================================ */
  /*  Fly-to helper                                                    */
  /* ================================================================ */

  private _startFly(toPos: THREE.Vector3, toLookAt: THREE.Vector3) {
    this._flyFrom.copy(this._camera.position);
    this._flyTo.copy(toPos);
    this._flyFromLookAt.copy(this._controls.target);
    this._flyTargetLookAt.copy(toLookAt);
    this._flyStartTime = this._clock.getElapsedTime();
    this._flyAnimating = true;
  }

  /* ================================================================ */
  /*  Filters & layout                                                 */
  /* ================================================================ */

  private _onLayoutChange(mode: "spiral" | "linear") {
    if (this._layoutMode === mode) return;
    this._layoutMode = mode;
    this._applyFilters();
  }

  /** Handler unifié pour les 4 filtres multi-select. */
  private _onFilterChange(
    filter: "building" | "firmware" | "model" | "function",
    e: Event
  ) {
    const selected = Array.from(
      (e.target as HTMLSelectElement).selectedOptions
    ).map((o) => o.value);
    if (filter === "building") this._filterHome = selected;
    if (filter === "firmware") this._filterFirmware = selected;
    if (filter === "model") this._filterModel = selected;
    if (filter === "function") this._filterFunction = selected;
    this._applyFilters();
  }

  private _clearFilter(filter: "building" | "firmware" | "model" | "function") {
    if (filter === "building") this._filterHome = [];
    if (filter === "firmware") this._filterFirmware = [];
    if (filter === "model") this._filterModel = [];
    if (filter === "function") this._filterFunction = [];
    this._applyFilters();
  }

  private _applyFilters() {
    if (!this._rawTree) return;
    if (this._focusedNode) this._releaseFocus();
    this._clearScene();

    // --- hierarchy filter ---
    const tree =
      this._filterHome.length > 0
        ? {
            ...this._rawTree,
            buildings: this._rawTree.buildings.filter((h) =>
              this._filterHome.includes(String(h.id))
            ),
          }
        : this._rawTree;

    // --- device filter (arrays vides = pas de filtre) ---
    let devices = [...this._rawDevices];
    if (this._filterFirmware.length > 0)
      devices = devices.filter(
        (d) =>
          d.firmwareId != null &&
          this._filterFirmware.includes(String(d.firmwareId))
      );
    if (this._filterModel.length > 0)
      devices = devices.filter(
        (d) =>
          d.modelId != null && this._filterModel.includes(String(d.modelId))
      );
    if (this._filterFunction.length > 0)
      devices = devices.filter(
        (d) =>
          d.functionId != null &&
          this._filterFunction.includes(String(d.functionId))
      );

    // --- reference node lists ---
    // Aucun filtre actif → tout afficher (nodes orphelins inclus).
    // Filtre actif → restreindre aux IDs utilisés par les devices visibles.
    const anyFilterActive =
      this._filterHome.length > 0 ||
      this._filterFirmware.length > 0 ||
      this._filterModel.length > 0 ||
      this._filterFunction.length > 0;

    let firmwares = this._rawFirmwares;
    let models = this._rawModels;
    let functions = this._rawFunctions;

    if (anyFilterActive) {
      const usedFwIds = new Set(
        devices.map((d) => d.firmwareId).filter((v): v is number => v != null)
      );
      const usedMdIds = new Set(
        devices.map((d) => d.modelId).filter((v): v is number => v != null)
      );
      const usedFnIds = new Set(
        devices.map((d) => d.functionId).filter((v): v is number => v != null)
      );
      firmwares = this._rawFirmwares.filter(
        (fw) => fw.id != null && usedFwIds.has(fw.id)
      );
      models = this._rawModels.filter(
        (m) => m.id != null && usedMdIds.has(m.id)
      );
      functions = this._rawFunctions.filter(
        (fn) => fn.id != null && usedFnIds.has(fn.id)
      );
    }

    this._nodes = [];
    this._edges = [];
    this._buildGraph(tree, devices, firmwares, models, functions);
  }

  /* ================================================================ */
  /*  Animation loop                                                   */
  /* ================================================================ */

  private _animate = () => {
    this._animId = requestAnimationFrame(this._animate);
    const t = this._clock.getElapsedTime();
    this._clock.getDelta();

    // Fly-to
    if (this._flyAnimating) {
      const ease = easeInOut(
        Math.min((t - this._flyStartTime) / this._flyDuration, 1)
      );
      this._camera.position.lerpVectors(this._flyFrom, this._flyTo, ease);
      this._controls.target.lerpVectors(
        this._flyFromLookAt,
        this._flyTargetLookAt,
        ease
      );
      if (ease >= 1) this._flyAnimating = false;
    }

    // Node bobbing
    for (const node of this._nodes) {
      if (!node.mesh) continue;
      const off = node.position.x * 0.1 + node.position.z * 0.1;
      node.mesh.position.y = node.position.y + Math.sin(t * 0.8 + off) * 0.3;
      node.mesh.rotation.y = t * 0.15 + off;
      if (node.labelSprite)
        node.labelSprite.position.y = node.mesh.position.y + node.radius + 1.2;
    }

    // Focus ring pulse
    if (this._focusRing && this._focusedNode?.mesh) {
      this._focusRing.position.copy(this._focusedNode.mesh.position);
      (this._focusRing.material as THREE.MeshBasicMaterial).opacity =
        0.25 + Math.sin(t * 3) * 0.1;
      this._focusRing.rotation.z = t * 0.5;
    }

    if (this._particleSystem) this._particleSystem.rotation.y = t * 0.02;

    // Hover raycasting
    this._raycaster.setFromCamera(this._mouse, this._camera);
    const meshes = this._nodes
      .map((n) => n.mesh)
      .filter(Boolean) as THREE.Mesh[];
    const hits = this._raycaster.intersectObjects(meshes);
    const tooltip = this.shadowRoot!.querySelector<HTMLDivElement>(".tooltip");

    if (hits.length > 0) {
      const nodeId = (hits[0].object as THREE.Mesh).userData.nodeId as string;
      const node = this._nodes.find((n) => n.id === nodeId) ?? null;
      if (node && node !== this._hoveredNode) {
        if (this._hoveredNode?.mesh && this._hoveredNode !== this._focusedNode)
          (
            this._hoveredNode.mesh.material as THREE.MeshStandardMaterial
          ).emissiveIntensity = this._getBaseEmissive(this._hoveredNode);
        this._hoveredNode = node;
        if (
          !this._focusedNode ||
          node === this._focusedNode ||
          this._getBaseEmissive(node) > 0
        )
          (
            (hits[0].object as THREE.Mesh)
              .material as THREE.MeshStandardMaterial
          ).emissiveIntensity = 0.65;
      }
      if (tooltip && node) {
        tooltip.classList.add("visible");
        tooltip.innerHTML = `<strong>${node.label}</strong><br/><em style="opacity:0.7">${node.type}</em><br/>${node.meta.replace(/\n/g, "<br/>")}`;
      }
    } else {
      if (this._hoveredNode?.mesh && this._hoveredNode !== this._focusedNode)
        (
          this._hoveredNode.mesh.material as THREE.MeshStandardMaterial
        ).emissiveIntensity = this._getBaseEmissive(this._hoveredNode);
      this._hoveredNode = null;
      tooltip?.classList.remove("visible");
    }

    this._controls.update();
    this._renderer.render(this._scene, this._camera);

    // ViewCube sync
    if (this._vcCube && this._vcRenderer) {
      const dir = new THREE.Vector3();
      this._camera.getWorldDirection(dir);
      this._vcCamera.position.copy(dir.negate().multiplyScalar(4));
      this._vcCamera.lookAt(0, 0, 0);
      this._vcRenderer.render(this._vcScene, this._vcCamera);
    }

    // FPS sampling (~1 s interval)
    this._dbgFrameCount++;
    const now = performance.now();
    if (this._dbgLastTime === 0) this._dbgLastTime = now;
    if (now - this._dbgLastTime >= 1000) {
      this._dbgFps = (this._dbgFrameCount * 1000) / (now - this._dbgLastTime);
      this._dbgFrameCount = 0;
      this._dbgLastTime = now;
      if (this._debugVisible) this._updateDebugOverlay();
    }
  };

  /* ================================================================ */
  /*  Events                                                           */
  /* ================================================================ */

  private _onResize = () => {
    const wrap = this.shadowRoot?.querySelector<HTMLDivElement>(".canvas-wrap");
    if (!wrap) return;
    this._camera.aspect = wrap.clientWidth / wrap.clientHeight;
    this._camera.updateProjectionMatrix();
    this._renderer.setSize(wrap.clientWidth, wrap.clientHeight);
  };

  private _onMouseDown = (e: MouseEvent) => {
    this._mouseDownPos = { x: e.clientX, y: e.clientY };
  };

  private _onMouseUp = (e: MouseEvent) => {
    const dx = e.clientX - this._mouseDownPos.x;
    const dy = e.clientY - this._mouseDownPos.y;
    if (Math.sqrt(dx * dx + dy * dy) > DmMapView.DRAG_THRESHOLD) return;
    this._handleNodeClick();
  };

  private _handleNodeClick() {
    this._raycaster.setFromCamera(this._mouse, this._camera);
    const meshes = this._nodes
      .map((n) => n.mesh)
      .filter(Boolean) as THREE.Mesh[];
    const hits = this._raycaster.intersectObjects(meshes);

    if (!hits.length) {
      if (this._focusedNode) this._releaseFocus();
      return;
    }

    const nodeId = (hits[0].object as THREE.Mesh).userData.nodeId as string;
    const node = this._nodes.find((n) => n.id === nodeId);
    if (!node) return;
    if (this._focusedNode === node) {
      this._releaseFocus();
      return;
    }

    if (this._focusedNode?.mesh)
      (
        this._focusedNode.mesh.material as THREE.MeshStandardMaterial
      ).emissiveIntensity = 0.25;
    this._clearFocusDimming();
    this._focusedNode = node;
    this._focusRelatedCache = null;
    this._applyFocusDimming(node.id);
    this._showFocusRing(node);
    this._focusOn(node);
  }

  private _onMouseMove = (e: MouseEvent) => {
    const wrap = this.shadowRoot?.querySelector<HTMLDivElement>(".canvas-wrap");
    if (!wrap) return;
    const rect = wrap.getBoundingClientRect();
    this._mouse.set(
      ((e.clientX - rect.left) / rect.width) * 2 - 1,
      -((e.clientY - rect.top) / rect.height) * 2 + 1
    );
    const tooltip = this.shadowRoot?.querySelector<HTMLDivElement>(".tooltip");
    if (tooltip) {
      tooltip.style.left = `${e.clientX - rect.left + 16}px`;
      tooltip.style.top = `${e.clientY - rect.top + 16}px`;
    }
  };

  /* ================================================================ */
  /*  Fullscreen & Debug                                               */
  /* ================================================================ */

  private _toggleFullscreen = () => {
    const wrap = this.shadowRoot?.querySelector<HTMLDivElement>(".canvas-wrap");
    if (!wrap) return;
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    } else {
      wrap.requestFullscreen().catch(() => {});
    }
  };

  private _onFullscreenChange = () => {
    this._isFullscreen = !!document.fullscreenElement;
    requestAnimationFrame(() => this._onResize());
  };

  private _toggleDebug = () => {
    this._debugVisible = !this._debugVisible;
    if (this._debugVisible)
      requestAnimationFrame(() => this._updateDebugOverlay());
  };

  private _updateDebugOverlay() {
    const overlay =
      this.shadowRoot?.querySelector<HTMLDivElement>(".debug-overlay");
    if (!overlay) return;
    const canvas = this.shadowRoot?.querySelector<HTMLCanvasElement>("canvas");
    const wrap = this.shadowRoot?.querySelector<HTMLDivElement>(".canvas-wrap");
    const mem = (
      performance as unknown as {
        memory?: { usedJSHeapSize: number; jsHeapSizeLimit: number };
      }
    ).memory;
    const fps = this._dbgFps;
    const fpsCls = fps >= 50 ? "fps-good" : fps >= 30 ? "fps-warn" : "fps-bad";
    const swKeys = [
      "llvmpipe",
      "softpipe",
      "swrast",
      "software",
      "microsoft basic",
    ];
    const isSW = swKeys.some((k) =>
      this._gpuRenderer.toLowerCase().includes(k)
    );

    overlay.innerHTML = `
      <div class="debug-title">⚙ DEBUG CONSOLE</div>
      <div class="debug-row"><span class="debug-key">FPS</span><span class="debug-val ${fpsCls}">${fps.toFixed(1)}</span></div>
      <div class="debug-row"><span class="debug-key">Résolution</span><span class="debug-val">${canvas?.width ?? 0}×${canvas?.height ?? 0}px</span></div>
      <div class="debug-row"><span class="debug-key">Affichage</span><span class="debug-val">${wrap?.clientWidth ?? 0}×${wrap?.clientHeight ?? 0}</span></div>
      <div class="debug-row"><span class="debug-key">DPR</span><span class="debug-val">${window.devicePixelRatio.toFixed(1)}</span></div>
      <hr class="debug-sep"/>
      <div class="debug-row"><span class="debug-key">GPU</span><span class="debug-val ${isSW ? "fps-bad" : "fps-good"}" style="font-size:10px;word-break:break-all">${isSW ? "⚠ " : ""}${this._gpuRenderer || "—"}</span></div>
      <div class="debug-row"><span class="debug-key">Vendor</span><span class="debug-val" style="font-size:10px">${this._gpuVendor || "—"}</span></div>
      <div class="debug-row"><span class="debug-key">WebGL</span><span class="debug-val">${this._renderer?.capabilities?.isWebGL2 ? "2.0" : "1.0"}</span></div>
      ${isSW ? `<div class="debug-row" style="color:#f87171;font-size:10px;margin-top:2px">⚠ Rendu logiciel détecté — GPU désactivé</div>` : ""}
      <hr class="debug-sep"/>
      ${
        mem
          ? `<div class="debug-row"><span class="debug-key">Mémoire JS</span><span class="debug-val">${(mem.usedJSHeapSize / 1024 / 1024).toFixed(1)} MB</span></div>
      <div class="debug-row"><span class="debug-key">Heap max</span><span class="debug-val">${(mem.jsHeapSizeLimit / 1024 / 1024).toFixed(0)} MB</span></div><hr class="debug-sep"/>`
          : ""
      }
      <div class="debug-row"><span class="debug-key">Triangles</span><span class="debug-val">${(this._renderer?.info?.render?.triangles ?? 0).toLocaleString()}</span></div>
      <div class="debug-row"><span class="debug-key">Draw calls</span><span class="debug-val">${this._renderer?.info?.render?.calls ?? 0}</span></div>
      <div class="debug-row"><span class="debug-key">Nœuds</span><span class="debug-val">${this._nodes.length}</span></div>
      <div class="debug-row"><span class="debug-key">Arêtes</span><span class="debug-val">${this._edges.length}</span></div>
      <hr class="debug-sep"/>
      ${
        this._camera
          ? `
      <div class="debug-row"><span class="debug-key">Cam X</span><span class="debug-val">${this._camera.position.x.toFixed(2)}</span></div>
      <div class="debug-row"><span class="debug-key">Cam Y</span><span class="debug-val">${this._camera.position.y.toFixed(2)}</span></div>
      <div class="debug-row"><span class="debug-key">Cam Z</span><span class="debug-val">${this._camera.position.z.toFixed(2)}</span></div>
      <hr class="debug-sep"/>`
          : ""
      }
      <div class="debug-row"><span class="debug-key">Layout</span><span class="debug-val">${this._layoutMode}</span></div>
    `;
  }

  private _resetCamera = () => {
    if (this._focusedNode) this._releaseFocus();
    this._startFly(new THREE.Vector3(0, 24, 55), new THREE.Vector3(0, 0, 0));
    this._controls.autoRotate = true;
  };

  /* ================================================================ */
  /*  Render template                                                  */
  /* ================================================================ */

  render() {
    const legendItems: [string, string][] = [
      ["#fbbf24", i18n.t("building")],
      ["#14b8a6", i18n.t("floor")],
      ["#6366f1", i18n.t("room")],
      ["#64748b", i18n.t("device")],
      ["#22d3ee", "Firmware"],
      ["#fb923c", "Model"],
      ["#a78bfa", "Function"],
    ];
    const filterDefs: {
      key: "building" | "firmware" | "model" | "function";
      label: string;
      opts: { id: string; name: string }[];
      val: string[];
    }[] = [
      {
        key: "building",
        label: i18n.t("building"),
        opts: this._homeOptions,
        val: this._filterHome,
      },
      {
        key: "firmware",
        label: "Firmware",
        opts: this._firmwareOptions,
        val: this._filterFirmware,
      },
      {
        key: "model",
        label: "Model",
        opts: this._modelOptions,
        val: this._filterModel,
      },
      {
        key: "function",
        label: "Function",
        opts: this._functionOptions,
        val: this._filterFunction,
      },
    ];

    return html`
      <div class="map-header">
        <h2>🗺️ ${i18n.t("nav_map")}</h2>
        <div class="legend">
          ${legendItems.map(
            ([color, label]) => html`
              <span class="legend-item">
                <span class="legend-dot" style="background:${color}"></span>
                ${label}
              </span>
            `
          )}
        </div>
      </div>

      <div class="filter-bar">
        ${filterDefs.map(
          ({ key, label, opts, val }) => html`
            <div class="filter-group">
              <label title="Ctrl+clic pour multi-sélection">${label}:</label>
              <select
                multiple
                size=${Math.min(Math.max(opts.length, 1), 5)}
                @change=${(e: Event) => this._onFilterChange(key, e)}
              >
                ${opts.map(
                  (o) =>
                    html`<option value=${o.id} .selected=${val.includes(o.id)}>
                      ${o.name}
                    </option>`
                )}
              </select>
              ${val.length > 0
                ? html`<button
                    class="filter-clear-btn"
                    title="Tout désélectionner"
                    @click=${() => this._clearFilter(key)}
                  >
                    ✕
                  </button>`
                : ""}
            </div>
          `
        )}
        <div class="layout-toggle">
          <button
            class=${`layout-btn${this._layoutMode === "spiral" ? " active" : ""}`}
            @click=${() => this._onLayoutChange("spiral")}
          >
            ⊛ Spiral
          </button>
          <button
            class=${`layout-btn${this._layoutMode === "linear" ? " active" : ""}`}
            @click=${() => this._onLayoutChange("linear")}
          >
            ⚌ Linéaire
          </button>
        </div>
      </div>

      <div class="canvas-wrap">
        <div class="viewcube-wrap"></div>
        <button
          class="overlay-btn fullscreen-btn"
          title="Toggle fullscreen"
          @click=${this._toggleFullscreen}
        >
          ${this._isFullscreen ? "⊠" : "⛶"}
        </button>
        <button
          class="overlay-btn reset-btn"
          title="Recadrer tout"
          @click=${this._resetCamera}
        >
          ⟳
        </button>
        <button
          class=${`overlay-btn debug-btn${this._debugVisible ? " active" : ""}`}
          title="Console de debug"
          @click=${this._toggleDebug}
        >
          ⚙
        </button>
        <div
          class=${`debug-overlay${this._debugVisible ? "" : " hidden"}`}
        ></div>
        ${this._loading
          ? html`<div class="loading-overlay">
              <span>${i18n.t("map_loading")}</span>
            </div>`
          : ""}
        <canvas></canvas>
        <div class="tooltip"></div>
      </div>

      <div class="stats-bar">
        <span
          ><strong>${this._stats.buildings}</strong> ${i18n.t(
            "buildings"
          )}</span
        >
        <span><strong>${this._stats.floors}</strong> ${i18n.t("floors")}</span>
        <span><strong>${this._stats.rooms}</strong> ${i18n.t("rooms")}</span>
        <span
          ><strong>${this._stats.devices}</strong> ${i18n.t("devices")}</span
        >
        <span><strong>${this._stats.firmwares}</strong> Firmwares</span>
        <span><strong>${this._stats.models}</strong> Models</span>
        <span><strong>${this._stats.functions}</strong> Functions</span>
      </div>
    `;
  }
}
