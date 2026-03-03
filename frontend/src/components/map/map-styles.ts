import { css } from "lit";

export const mapStyles = css`
  :host {
    display: block;
  }

  .map-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    flex-wrap: wrap;
    gap: 12px;
  }
  .map-header h2 {
    margin: 0;
    font-size: 20px;
  }

  .legend {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    font-size: 13px;
    color: var(--dm-text-secondary, #64748b);
  }
  .legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .legend-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    display: inline-block;
  }

  .canvas-wrap {
    position: relative;
    width: 100%;
    height: 70vh;
    min-height: 420px;
    border-radius: 12px;
    overflow: hidden;
    background: linear-gradient(135deg, #d1d5db 0%, #e5e7eb 100%);
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.12);
  }
  .canvas-wrap:fullscreen,
  .canvas-wrap:-webkit-full-screen {
    width: 100vw;
    height: 100vh;
    border-radius: 0;
  }

  /* --- overlay buttons (fullscreen / reset / debug) --- */
  .overlay-btn {
    position: absolute;
    right: 12px;
    z-index: 15;
    background: rgba(255, 255, 255, 0.7);
    border: 1px solid rgba(100, 116, 139, 0.3);
    color: #334155;
    width: 36px;
    height: 36px;
    border-radius: 8px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(8px);
    transition: background 0.15s;
  }
  .overlay-btn:hover {
    background: rgba(255, 255, 255, 0.9);
  }
  .fullscreen-btn {
    top: 12px;
    font-size: 18px;
  }
  .reset-btn {
    top: 56px;
    font-size: 15px;
  }
  .debug-btn {
    top: 100px;
    font-size: 14px;
  }
  .debug-btn.active {
    background: rgba(15, 23, 42, 0.75);
    color: #7dd3fc;
    border-color: rgba(125, 211, 252, 0.4);
  }

  /* --- debug overlay --- */
  .debug-overlay {
    position: absolute;
    bottom: 12px;
    left: 12px;
    z-index: 15;
    background: rgba(2, 6, 23, 0.55);
    color: #e2e8f0;
    font-family: "Courier New", Courier, monospace;
    font-size: 11.5px;
    line-height: 1.7;
    padding: 10px 14px;
    border-radius: 10px;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    min-width: 210px;
    pointer-events: none;
    transition: opacity 0.2s;
  }
  .debug-overlay.hidden {
    opacity: 0;
    pointer-events: none;
    display: none;
  }
  .debug-title {
    font-size: 10px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #7dd3fc;
    margin-bottom: 6px;
    font-weight: 700;
  }
  .debug-row {
    display: flex;
    justify-content: space-between;
    gap: 14px;
  }
  .debug-key {
    color: #94a3b8;
  }
  .debug-val {
    color: #f1f5f9;
    font-weight: 600;
  }
  .debug-val.fps-good {
    color: #4ade80;
  }
  .debug-val.fps-warn {
    color: #fbbf24;
  }
  .debug-val.fps-bad {
    color: #f87171;
  }
  .debug-sep {
    border: none;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    margin: 4px 0;
  }

  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }

  .tooltip {
    position: absolute;
    pointer-events: none;
    background: rgba(255, 255, 255, 0.92);
    color: #1e293b;
    padding: 8px 14px;
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.4;
    max-width: 260px;
    opacity: 0;
    transition: opacity 0.15s;
    z-index: 10;
    border: 1px solid rgba(100, 116, 139, 0.2);
    backdrop-filter: blur(8px);
  }
  .tooltip.visible {
    opacity: 1;
  }

  .stats-bar {
    margin-top: 12px;
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
    font-size: 13px;
    color: var(--dm-text-secondary, #64748b);
  }
  .stats-bar strong {
    color: var(--dm-text, #1e293b);
  }

  .loading-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #1e293b;
    font-size: 16px;
    background: rgba(229, 231, 235, 0.85);
    z-index: 20;
  }
  @keyframes pulse {
    0%,
    100% {
      opacity: 1;
    }
    50% {
      opacity: 0.4;
    }
  }
  .loading-overlay span {
    animation: pulse 1.5s ease-in-out infinite;
  }

  /* --- filter bar --- */
  .filter-bar {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    align-items: flex-start;
    margin-bottom: 12px;
    font-size: 13px;
  }
  .filter-bar label {
    color: var(--dm-text-secondary, #64748b);
    font-weight: 600;
    margin-right: 2px;
  }
  .filter-bar select {
    padding: 5px 10px;
    border-radius: 6px;
    border: 1px solid rgba(100, 116, 139, 0.3);
    background: rgba(255, 255, 255, 0.85);
    color: #1e293b;
    font-size: 13px;
    cursor: pointer;
    backdrop-filter: blur(4px);
    min-width: 120px;
  }
  .filter-bar select:focus {
    outline: 2px solid #6366f1;
    outline-offset: 1px;
  }
  .filter-bar select[multiple] {
    min-height: 28px;
    max-height: 120px;
    cursor: pointer;
    padding: 2px 6px;
  }
  .filter-group {
    display: flex;
    align-items: flex-start;
    gap: 4px;
  }
  .filter-group label {
    padding-top: 5px;
  }
  .filter-clear-btn {
    background: none;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    font-size: 13px;
    padding: 3px 5px;
    border-radius: 4px;
    line-height: 1;
    margin-top: 2px;
    transition: color 0.15s;
  }
  .filter-clear-btn:hover {
    color: #ef4444;
  }

  /* --- layout toggle --- */
  .layout-toggle {
    display: flex;
    gap: 4px;
    margin-left: auto;
    align-items: center;
    align-self: center;
  }
  .layout-btn {
    padding: 5px 10px;
    border-radius: 6px;
    border: 1px solid rgba(100, 116, 139, 0.3);
    background: rgba(255, 255, 255, 0.85);
    color: #1e293b;
    font-size: 13px;
    cursor: pointer;
    backdrop-filter: blur(4px);
    transition:
      background 0.15s,
      color 0.15s;
    white-space: nowrap;
  }
  .layout-btn:hover {
    background: rgba(255, 255, 255, 0.95);
  }
  .layout-btn.active {
    background: #6366f1;
    color: #fff;
    border-color: #6366f1;
  }

  /* --- ViewCube --- */
  .viewcube-wrap {
    position: absolute;
    top: 12px;
    right: 56px;
    width: 100px;
    height: 100px;
    z-index: 15;
    cursor: pointer;
    border-radius: 8px;
    overflow: hidden;
    background: rgba(255, 255, 255, 0.25);
    backdrop-filter: blur(6px);
  }
  .viewcube-wrap canvas {
    width: 100px !important;
    height: 100px !important;
  }
`;
