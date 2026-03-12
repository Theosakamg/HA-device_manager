---
description: "Download a **full snapshot** of all your devices in the format of your choice."
---

The export produces a single file containing all devices with their complete set of fields (MAC, IP, model, firmware, function, room, position, MQTT topic, hostname, FQDN, etc.).

## Formats

| Format | Best for |
|---|---|
| **CSV** | Spreadsheet editing, re-import after bulk changes |
| **JSON** | API integration, scripting, backup |
| **YAML** | Human-readable config files, GitOps workflows |

## Recommended workflow

1. **Export to CSV** before any bulk operation
2. Edit the file in your spreadsheet tool
3. **Re-import** via the Import section to apply changes

> **Before the Danger Zone:** always export first — it's your only rollback option.
