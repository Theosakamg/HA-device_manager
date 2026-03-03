/**
 * Shared CSS styles for Device Manager components.
 */
import { css } from "lit";

export const sharedStyles = css`
  :host {
    display: block;
    font-family:
      -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue",
      Arial, sans-serif;
    color: var(--primary-text-color, #212121);
    --dm-primary: #03a9f4;
    --dm-primary-dark: #0288d1;
    --dm-accent: #ff9800;
    --dm-error: #f44336;
    --dm-success: #4caf50;
    --dm-bg: #f5f5f5;
    --dm-card-bg: #ffffff;
    --dm-border: #e0e0e0;
    --dm-text: #212121;
    --dm-text-secondary: #757575;
    --dm-radius: 8px;
    --dm-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  /* Card styles */
  .card {
    background: var(--dm-card-bg);
    border-radius: var(--dm-radius);
    box-shadow: var(--dm-shadow);
    padding: 16px;
    margin-bottom: 16px;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--dm-border);
  }

  .card-header h2,
  .card-header h3 {
    margin: 0;
    font-weight: 500;
  }

  /* Button styles */
  button,
  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition:
      background-color 0.2s,
      opacity 0.2s;
  }

  button:disabled,
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-primary {
    background: var(--dm-primary);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--dm-primary-dark);
  }

  .btn-danger {
    background: var(--dm-error);
    color: white;
  }

  .btn-danger:hover:not(:disabled) {
    background: #d32f2f;
  }

  .btn-secondary {
    background: #e0e0e0;
    color: var(--dm-text);
  }

  .btn-secondary:hover:not(:disabled) {
    background: #bdbdbd;
  }

  .btn-icon {
    padding: 6px;
    background: none;
    border-radius: 50%;
    min-width: 32px;
    min-height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }

  .btn-icon:hover:not(:disabled) {
    background: rgba(0, 0, 0, 0.08);
  }

  /* Form styles */
  .form-group {
    margin-bottom: 12px;
  }

  .form-group label {
    display: block;
    font-size: 12px;
    font-weight: 500;
    color: var(--dm-text-secondary);
    margin-bottom: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .form-group input,
  .form-group select,
  .form-group textarea {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid var(--dm-border);
    border-radius: 4px;
    font-size: 14px;
    box-sizing: border-box;
    transition: border-color 0.2s;
  }

  .form-group input:focus,
  .form-group select:focus,
  .form-group textarea:focus {
    outline: none;
    border-color: var(--dm-primary);
    box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  /* Table styles */
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }

  th {
    text-align: left;
    padding: 10px 12px;
    font-weight: 600;
    color: var(--dm-text-secondary);
    border-bottom: 2px solid var(--dm-border);
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--dm-border);
    vertical-align: middle;
  }

  /* Action column: align icons to the right */
  th:last-child,
  td:last-child {
    text-align: right;
    white-space: nowrap;
  }

  tr:hover {
    background: rgba(0, 0, 0, 0.02);
  }

  /* Badge */
  .badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 6px;
    border-radius: 10px;
    font-size: 11px;
    font-weight: 600;
    background: #e0e0e0;
    color: var(--dm-text-secondary);
  }

  .badge-success {
    background: var(--dm-success);
  }

  .badge-error {
    background: var(--dm-error);
  }

  /* Status dot */
  .status-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
  }

  .status-enabled {
    background: var(--dm-success);
  }

  .status-disabled {
    background: var(--dm-error);
  }

  /* Modal overlay */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: var(--dm-card-bg);
    border-radius: var(--dm-radius);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    max-width: 600px;
    width: 90%;
    max-height: 90vh;
    overflow-y: auto;
    padding: 24px;
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }

  .modal-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 500;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--dm-border);
  }

  /* Toast/alert */
  .toast {
    position: fixed;
    bottom: 20px;
    right: 20px;
    padding: 12px 24px;
    border-radius: 4px;
    color: white;
    font-size: 14px;
    z-index: 2000;
    animation: slideIn 0.3s ease-out;
  }

  .toast-success {
    background: var(--dm-success);
  }

  .toast-error {
    background: var(--dm-error);
  }

  @keyframes slideIn {
    from {
      transform: translateX(100%);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  /* Empty state */
  .empty-state {
    text-align: center;
    padding: 40px 20px;
    color: var(--dm-text-secondary);
  }

  .empty-state ha-icon {
    --mdc-icon-size: 48px;
    color: var(--dm-border);
    margin-bottom: 12px;
  }

  /* Tabs */
  .tabs {
    display: flex;
    border-bottom: 2px solid var(--dm-border);
    margin-bottom: 16px;
  }

  .tab {
    padding: 10px 20px;
    cursor: pointer;
    font-weight: 500;
    color: var(--dm-text-secondary);
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    transition:
      color 0.2s,
      border-color 0.2s;
    background: none;
    border-top: none;
    border-left: none;
    border-right: none;
  }

  .tab:hover {
    color: var(--dm-primary);
  }

  .tab.active {
    color: var(--dm-primary);
    border-bottom-color: var(--dm-primary);
  }

  /* Loading spinner */
  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 40px;
    color: var(--dm-text-secondary);
  }

  /* Result/stats panel – shared by import-view & deploy-modal */
  .stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 12px;
    margin: 16px 0;
  }
  .stat-box {
    text-align: center;
    padding: 16px;
    border-radius: 8px;
    background: #f5f5f5;
  }
  .stat-value {
    font-size: 24px;
    font-weight: bold;
  }
  .stat-label {
    font-size: 12px;
    color: var(--dm-text-secondary);
    margin-top: 4px;
  }
  .stat-box.success,
  .stat-box.created,
  .stat-box.devices {
    background: #e8f5e9;
    color: #2e7d32;
  }
  .stat-box.info,
  .stat-box.updated,
  .stat-box.selected {
    background: #e3f2fd;
    color: #1565c0;
  }
  .stat-box.warning,
  .stat-box.skipped,
  .stat-box.no-match {
    background: #fff3e0;
    color: #ef6c00;
  }
  .stat-box.errors {
    background: #fce4ec;
    color: #c62828;
    cursor: pointer;
  }
  .stat-box.errors:hover {
    background: #f8bbd0;
  }
  .log-table {
    max-height: 300px;
    overflow-y: auto;
  }
  .log-table table {
    font-size: 13px;
  }
  .error-panel {
    margin-top: 16px;
    border: 1px solid #e57373;
    border-radius: 8px;
    background: #ffebee;
    overflow: hidden;
  }
  .error-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: #ef9a9a;
    color: #b71c1c;
    font-weight: 600;
    cursor: pointer;
    user-select: none;
  }
  .error-panel-header:hover {
    background: #e57373;
  }
  .error-panel-body {
    max-height: 300px;
    overflow-y: auto;
    padding: 0;
  }
  .error-list {
    list-style: none;
    margin: 0;
    padding: 0;
  }
  .error-list li {
    padding: 8px 16px;
    border-bottom: 1px solid #ffcdd2;
    font-size: 13px;
    color: #b71c1c;
    font-family: monospace;
  }
  .error-list li:last-child {
    border-bottom: none;
  }

  /* Responsive */
  @media (max-width: 768px) {
    .form-row {
      grid-template-columns: 1fr;
    }

    .modal {
      width: 95%;
      padding: 16px;
    }
  }
`;
