---
description: "Tools for **data management**, network discovery, and configuration of the Device Manager."
---

The Maintenance section groups all administrative operations that fall outside day-to-day device management. Use it to configure global network parameters, export a snapshot of your data, import devices in bulk, discover new devices on the network, or perform destructive cleanup operations.

## Sections

| Section | Purpose |
|---|---|
| ⚙️ **Configuration** | Set IP prefix, DNS suffix, MQTT prefix and default building name |
| 📤 **Export** | Download a full snapshot in CSV, JSON or YAML |
| 📥 **Import** | Bulk-create devices from a CSV file |
| 🔍 **Scan Network** | Trigger a network scan to discover and update device IPs |
| ⚠️ **Danger Zone** | Irreversible operations — clean the database or reset IP cache |

> **Tip:** Run an **Export** before any operation in the Danger Zone so you always have a rollback snapshot.
